from loguru import logger

from src.config import settings
from src.db.report.pipeline_repository import ReportPipelineRepository
from src.llm import client_factory
from src.models.reports.generation import GeneratedReportSection, GeneratedReportSectionList
from src.models.reports.pipeline import (
    ReportPipelineContext,
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.prompts.report_generation import REPORT_GENERATION_PROMPT


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes}:{remaining_seconds:02d}"


def format_transcription_segments_for_prompt(
    segment_rows: list[StoredTranscriptionSegment],
) -> str:
    return "\n".join(
        (
            f"{segment_index}. [{format_timestamp(segment.start_seconds)}-"
            f'{format_timestamp(segment.end_seconds)}] "{segment.text}"'
        )
        for segment_index, segment in enumerate(segment_rows, start=1)
    )


def _format_dji_metadata(meta: dict) -> str:
    fields = [
        ("captured_at", meta.get("utc_at_exposure")),
        ("image_source", meta.get("image_source")),
        ("drone", meta.get("drone_model")),
        ("lrf_lat", meta.get("lrf_target_lat")),
        ("lrf_lon", meta.get("lrf_target_lon")),
        ("lrf_alt", meta.get("lrf_target_alt")),
        ("gimbal_yaw", meta.get("gimbal_yaw_degree")),
    ]
    parts = [f"{k}={v}" for k, v in fields if v is not None]
    return f"[Metadata: {', '.join(parts)}]" if parts else ""


def _format_thermal_metrics(metrics: dict) -> str:
    panels = metrics.get("panels", [])
    if not panels:
        return ""
    lines = ["[Thermische meting per paneel (kader-pixels uitgesloten):"]
    for p in panels:
        lines.append(
            f"  Paneel {p['panel_index']} (rij {p['row']}, kolom {p['col']}): "
            f"Tmin={p['tmin_c']}°C  Tmax={p['tmax_c']}°C  Tgem={p['tgem_c']}°C  ΔT={p['delta_t_c']}°C"
        )
    lines.append("]")
    return "\n".join(lines)


def format_images_for_prompt(image_rows: list[StoredImageAnalysis]) -> str:
    lines = []
    for image_index, image in enumerate(image_rows, start=1):
        line = f"{image_index}. {image.analysis_text}"
        if image.dji_metadata:
            meta_str = _format_dji_metadata(image.dji_metadata)
            if meta_str:
                line += f"\n{meta_str}"
        if image.thermal_metrics:
            line += f"\n{_format_thermal_metrics(image.thermal_metrics)}"
        if image.panel_location_key:
            line += f"\n[Locatiefoto paneel: {image.panel_location_key}]"
        lines.append(line)
    return "\n".join(lines)


def build_report_generation_prompt(
    template_structure: TemplateStructure,
    template_sections: list[TemplateSection],
    segment_rows: list[StoredTranscriptionSegment],
    image_rows: list[StoredImageAnalysis],
    report: ReportPipelineContext,
) -> str:
    sections_text = "\n".join(
        f"- id: {section.id}, label: {section.label}" for section in template_sections
    )
    transcription_segments_text = format_transcription_segments_for_prompt(segment_rows)
    image_text = format_images_for_prompt(image_rows)
    metadata_values = report.metadata.model_dump()
    metadata_context = [
        f"{metadata_field.label}: {metadata_values[metadata_field.key]}"
        for metadata_field in template_structure.metadata_fields
        if metadata_field.key in metadata_values
    ]
    extra_context = "\n".join(
        [
            *metadata_context,
            *([f"Extra opmerkingen: {report.extra_context}"] if report.extra_context else []),
        ]
    )
    context_text = f"\nExtra context:\n{extra_context}\n" if extra_context else ""

    return REPORT_GENERATION_PROMPT.format(
        sections_text=sections_text,
        transcription_segments_text=transcription_segments_text,
        image_text=image_text,
        context_text=context_text,
    )


async def generate_report_sections(
    report: ReportPipelineContext,
    template_structure: TemplateStructure,
    template_sections: list[TemplateSection],
    segment_rows: list[StoredTranscriptionSegment],
    image_rows: list[StoredImageAnalysis],
) -> list[GeneratedReportSection]:
    prompt = build_report_generation_prompt(
        template_structure,
        template_sections,
        segment_rows,
        image_rows,
        report,
    )
    client = client_factory.get_gpt4o_client()
    response = await client.chat.completions.create(
        model=settings.gpt4o_deployment,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    payload = GeneratedReportSectionList.model_validate_json(content)
    return payload.sections


async def persist_pipeline_results(
    repository: ReportPipelineRepository,
    report: ReportPipelineContext,
    template_sections: list[TemplateSection],
    generated_sections: list[GeneratedReportSection],
    segment_rows: list[StoredTranscriptionSegment],
    image_rows: list[StoredImageAnalysis],
) -> None:
    template_sections_by_id = {section.id: section for section in template_sections}
    section_pairs: list[tuple[GeneratedReportSection, TemplateSection]] = []

    for section_data in generated_sections:
        try:
            template_section = template_sections_by_id[section_data.id]
        except KeyError:
            logger.warning("Skipping unknown generated report section id {}", section_data.id)
            continue

        section_pairs.append((section_data, template_section))

    report_section_ids = await repository.insert_report_sections(
        str(report.id),
        str(report.company_id),
        section_pairs,
    )

    for report_section_id, (section_data, _) in zip(
        report_section_ids,
        section_pairs,
        strict=True,
    ):
        for transcription_ref in section_data.transcription_refs:
            if transcription_ref < 1 or transcription_ref > len(segment_rows):
                continue
            transcription_segment_id = str(segment_rows[transcription_ref - 1].id)
            await repository.insert_report_section_source_transcription(
                report_section_id,
                transcription_segment_id,
            )

        for image_ref in section_data.image_refs:
            if image_ref < 1 or image_ref > len(image_rows):
                continue
            image_analysis_id = str(image_rows[image_ref - 1].id)
            await repository.insert_report_section_source_image(
                report_section_id,
                image_analysis_id,
            )
