from pathlib import Path

import asyncpg
from loguru import logger

from src.config import settings
from src.db import inspection_queries, report_queries, template_queries
from src.db.connection import get_connection_url
from src.db.report_pipeline_repository import ReportPipelineRepository
from src.llm import client_factory, gpt4o_client, gpt4o_transcribe_client
from src.models.reports.generation import GeneratedReportSection, GeneratedReportSectionList
from src.models.reports.pipeline import (
    ReportPipelineContext,
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.prompts.report_generation import REPORT_GENERATION_PROMPT
from src.storage import blob


async def run_audio_pipeline(report_id: str) -> None:
    report = await report_queries.get_report_for_pipeline(report_id)
    template_structure = await template_queries.fetch_template_structure(
        str(report.template_id),
        str(report.company_id),
    )
    template_sections = template_structure.sections

    try:
        connection = await asyncpg.connect(get_connection_url())
        try:
            async with connection.transaction():
                repository = ReportPipelineRepository(connection)
                await transcribe_inspection_audio_files(report, repository)
                await analyze_inspection_photo_files(report, repository)
                segment_rows = await repository.fetch_transcription_segments_for_inspection(
                    str(report.inspection_id)
                )
                image_rows = await repository.fetch_image_analyses_for_inspection(
                    str(report.inspection_id)
                )
                parsed_sections = await generate_report_sections(
                    report,
                    template_structure,
                    template_sections,
                    segment_rows,
                    image_rows,
                )
                await persist_pipeline_results(
                    repository,
                    report,
                    template_sections,
                    parsed_sections,
                    segment_rows,
                    image_rows,
                )
        finally:
            await connection.close()

        await report_queries.set_report_status(report_id, "draft")
    except Exception as error:
        await report_queries.set_report_status(report_id, "failed")
        logger.exception("Report {} generation failed: {}", report_id, error)
        raise


async def transcribe_inspection_audio_files(
    report: ReportPipelineContext,
    repository: ReportPipelineRepository,
) -> None:
    audio_files = await inspection_queries.fetch_inspection_audio_files(str(report.inspection_id))

    for audio_file in audio_files:
        audio_key = audio_file.storage_key
        try:
            file_content = await blob.download_file("inspections", audio_key)
            result = await gpt4o_transcribe_client.transcribe_audio(
                file_content,
                audio_file.original_file_name,
            )
            transcription_id = await repository.insert_transcription(
                str(report.inspection_id),
                str(report.company_id),
                audio_key,
                result.full_text,
                result.duration_seconds,
            )
            segment_ids = await repository.insert_transcription_segments(
                transcription_id,
                str(report.inspection_id),
                result.segments,
            )
            logger.info(
                "Transcribed {} into {} segment(s), duration={}s, chars={}",
                audio_key,
                len(segment_ids),
                result.duration_seconds,
                len(result.full_text),
            )
        except Exception:
            logger.exception("Audio file {} failed", audio_key)
            raise


async def analyze_inspection_photo_files(
    report: ReportPipelineContext,
    repository: ReportPipelineRepository,
) -> None:
    photo_files = await inspection_queries.fetch_inspection_photo_files(str(report.inspection_id))

    for photo_file in photo_files:
        photo_key = photo_file.storage_key
        try:
            file_content = await blob.download_file("inspections", photo_key)
            description = await gpt4o_client.analyze_inspection_photo(
                Path(photo_key).name,
                file_content,
            )
            image_analysis_id = await repository.insert_image_analysis(
                str(report.inspection_id),
                str(report.company_id),
                photo_key,
                description,
            )
            logger.info("Analyzed photo {} as image_analysis {}", photo_key, image_analysis_id)
        except Exception:
            logger.exception("Photo file {} failed", photo_key)
            raise


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

    for section_data in generated_sections:
        template_section = template_sections_by_id[section_data.id]
        report_section_id = await repository.insert_report_section(
            str(report.id),
            str(report.company_id),
            section_data,
            template_section,
        )

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
