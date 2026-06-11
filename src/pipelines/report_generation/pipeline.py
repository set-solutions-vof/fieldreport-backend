from loguru import logger

from src.db.connection import get_database
from src.db.report import queries
from src.db.report.pipeline_repository import ReportPipelineRepository
from src.db.template.queries import fetch_template_structure
from src.pipelines.report_generation.generation import (
    generate_report_sections,
    persist_pipeline_results,
)
from src.pipelines.report_generation.image_analysis import analyze_inspection_photo_files
from src.pipelines.report_generation.transcription import transcribe_inspection_audio_files


async def run_report_generation(report_id: str) -> None:
    report = await queries.get_report_for_pipeline(report_id)
    template_structure = await fetch_template_structure(
        str(report.template_id),
        str(report.company_id),
    )
    template_sections = template_structure.sections

    try:
        async with get_database().acquire() as connection:
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

        await queries.set_report_status(report_id, "draft")
    except Exception as error:
        await queries.set_report_status(report_id, "failed")
        logger.exception("Report {} generation failed: {}", report_id, error)
        raise
