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
    combined_transcription = "\n".join(segment.text for segment in segment_rows)
    image_text = "\n".join(
        f"{image_index}. {image.analysis_text}"
        for image_index, image in enumerate(image_rows, start=1)
    )
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
        combined_transcription=combined_transcription,
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
    transcription_segment_ids = [str(segment.id) for segment in segment_rows]
    image_analysis_ids = [str(image.id) for image in image_rows]
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

    for report_section_id in report_section_ids:
        for transcription_segment_id in transcription_segment_ids:
            await repository.insert_report_section_source_transcription(
                report_section_id,
                transcription_segment_id,
            )

        for image_analysis_id in image_analysis_ids:
            await repository.insert_report_section_source_image(
                report_section_id,
                image_analysis_id,
            )
