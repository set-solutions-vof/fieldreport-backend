from pathlib import Path

from loguru import logger

from src.config import settings
from src.db import inspection_queries, report_queries, template_queries
from src.llm import client_factory, gpt4o_client, gpt4o_transcribe_client
from src.models.reports.generation import GeneratedReportSection, GeneratedReportSectionList
from src.models.reports.pipeline import (
    ReportPipelineContext,
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.prompts.report_generation import REPORT_GENERATION_PROMPT
from src.storage import inspection_file_storage


async def run_audio_pipeline(report_id: str) -> None:
    report = await report_queries.get_report_for_pipeline(report_id)
    inspection_id = str(report.inspection_id)
    company_id = str(report.company_id)
    template_structure = await template_queries.fetch_template_structure(
        str(report.template_id), company_id
    )
    template_sections = template_structure.sections

    await transcribe_inspection_audio_files(inspection_id, company_id)
    await analyze_inspection_photo_files(inspection_id, company_id)

    segment_rows = await report_queries.fetch_transcription_segments_for_inspection(inspection_id)
    image_rows = await report_queries.fetch_image_analyses_for_inspection(inspection_id)

    try:
        parsed_sections = await generate_report_sections(
            report,
            template_structure,
            template_sections,
            segment_rows,
            image_rows,
        )
        await persist_report_sections(
            report_id,
            company_id,
            template_sections,
            parsed_sections,
            segment_rows,
            image_rows,
        )
        await report_queries.set_report_status(report_id, "draft")
    except Exception as error:
        await report_queries.set_report_status(report_id, "failed")
        logger.exception("Report {} generation failed: {}", report_id, error)
        raise


async def transcribe_inspection_audio_files(inspection_id: str, company_id: str) -> None:
    audio_files = await inspection_queries.fetch_inspection_audio_files(inspection_id)

    for audio_file in audio_files:
        audio_key = audio_file.storage_key
        try:
            file_content = inspection_file_storage.load_inspection_file(audio_key)
            result = await gpt4o_transcribe_client.transcribe_audio(
                file_content,
                audio_file.original_file_name,
            )
            transcription_id = await report_queries.insert_transcription(
                inspection_id,
                company_id,
                audio_key,
                result.full_text,
                result.duration_seconds,
            )
            segment_ids = await report_queries.insert_transcription_segments(
                transcription_id,
                inspection_id,
                result.segments,
            )
            logger.info(
                "Transcribed {} into {} segment(s), duration={}s, chars={}",
                audio_key,
                len(segment_ids),
                result.duration_seconds,
                len(result.full_text),
            )
        except Exception as error:
            logger.error("Audio file {} failed: {}", audio_key, error)


async def analyze_inspection_photo_files(inspection_id: str, company_id: str) -> None:
    photo_files = await inspection_queries.fetch_inspection_photo_files(inspection_id)

    for photo_file in photo_files:
        photo_key = photo_file.storage_key
        try:
            file_content = inspection_file_storage.load_inspection_file(photo_key)
            description = await gpt4o_client.analyze_inspection_photo(
                Path(photo_key).name,
                file_content,
            )
            image_analysis_id = await report_queries.insert_image_analysis(
                inspection_id,
                company_id,
                photo_key,
                description,
            )
            logger.info("Analyzed photo {} as image_analysis {}", photo_key, image_analysis_id)
        except Exception as error:
            logger.error("Photo file {} failed: {}", photo_key, error)


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


async def persist_report_sections(
    report_id: str,
    company_id: str,
    template_sections: list[TemplateSection],
    generated_sections: list[GeneratedReportSection],
    segment_rows: list[StoredTranscriptionSegment],
    image_rows: list[StoredImageAnalysis],
) -> None:
    template_sections_by_id = {section.id: section for section in template_sections}
    transcription_segment_ids = [str(segment.id) for segment in segment_rows]
    image_analysis_ids = [str(image.id) for image in image_rows]

    for section_data in generated_sections:
        template_section = template_sections_by_id[section_data.id]
        report_section_id = await report_queries.insert_report_section(
            report_id,
            company_id,
            section_data.id,
            template_section.order,
            template_section.render_type,
            section_data.generated_content,
            section_data.confidence_level,
            section_data.confidence_score,
        )

        for transcription_segment_id in transcription_segment_ids:
            await report_queries.insert_report_section_source_transcription(
                report_section_id,
                transcription_segment_id,
            )

        for image_analysis_id in image_analysis_ids:
            await report_queries.insert_report_section_source_image(
                report_section_id,
                image_analysis_id,
            )
