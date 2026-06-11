from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.db.report.pipeline_repository import ReportPipelineRepository
from src.models.reports.generation import GeneratedReportSection
from src.models.reports.pipeline import (
    StoredImageAnalysis,
    StoredTranscriptionSegment,
)
from src.models.templates.domain import (
    TemplateScalarMetadataField,
    TemplateSection,
    TemplateSelectMetadataField,
    TemplateStructure,
)
from src.pipelines.report_generation import pipeline
from tests.pipelines.helpers import build_pipeline_connection, build_report


async def test_run_report_generation_processes_media_and_persists_sections() -> None:
    report = build_report()
    segment_id = uuid4()
    image_id = uuid4()
    template_structure = TemplateStructure(
        metadata_fields=[
            TemplateSelectMetadataField(
                key="type_onderzoek",
                label="Type onderzoek",
                type="select",
                options=["Lekdetectie"],
            ),
            TemplateScalarMetadataField(
                key="type_klant",
                label="Type klant",
                type="text",
            ),
        ],
        sections=[
            TemplateSection(
                id="conclusie",
                label="Conclusie",
                order=1,
                render_type="text_block",
            )
        ],
    )
    generated_section = GeneratedReportSection(
        id="conclusie",
        generated_content="Concept",
        confidence_level="high",
        confidence_score=0.9,
    )
    connection = build_pipeline_connection()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            pipeline.queries,
            "get_report_for_pipeline",
            AsyncMock(return_value=report),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.fetch_template_structure",
            AsyncMock(return_value=template_structure),
        ),
        patch("src.pipelines.report_generation.pipeline.get_database", return_value=pool),
        patch(
            "src.pipelines.report_generation.pipeline.transcribe_inspection_audio_files",
            AsyncMock(),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.analyze_inspection_photo_files",
            AsyncMock(),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_transcription_segments_for_inspection",
            AsyncMock(
                return_value=[
                    StoredTranscriptionSegment(
                        id=segment_id,
                        text="Inspecteur noemt vocht.",
                    )
                ]
            ),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[StoredImageAnalysis(id=image_id, analysis_text="Fotoanalyse")]),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.generate_report_sections",
            AsyncMock(
                return_value=[generated_section],
            ),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.persist_pipeline_results",
            AsyncMock(),
        ) as persist_results,
        patch.object(pipeline.queries, "set_report_status", AsyncMock()) as set_status,
    ):
        await pipeline.run_report_generation("report-id")

    persist_results.assert_awaited_once()
    set_status.assert_awaited_once_with("report-id", "draft")


async def test_run_report_generation_marks_failed_when_transcription_fails() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )
    connection = build_pipeline_connection()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            pipeline.queries,
            "get_report_for_pipeline",
            AsyncMock(return_value=report),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.fetch_template_structure",
            AsyncMock(return_value=template_structure),
        ),
        patch("src.pipelines.report_generation.pipeline.get_database", return_value=pool),
        patch(
            "src.pipelines.report_generation.pipeline.transcribe_inspection_audio_files",
            AsyncMock(side_effect=ValueError("missing file")),
        ),
        patch.object(pipeline.queries, "set_report_status", AsyncMock()) as set_status,
    ):
        with pytest.raises(ValueError, match="missing file"):
            await pipeline.run_report_generation("report-id")

    set_status.assert_awaited_once_with("report-id", "failed")


async def test_run_report_generation_marks_failed_when_report_generation_fails() -> None:
    report = build_report()
    template_structure = TemplateStructure(
        sections=[TemplateSection(id="conclusie", label="Conclusie", render_type="text_block")]
    )
    connection = build_pipeline_connection()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(
            pipeline.queries,
            "get_report_for_pipeline",
            AsyncMock(return_value=report),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.fetch_template_structure",
            AsyncMock(return_value=template_structure),
        ),
        patch("src.pipelines.report_generation.pipeline.get_database", return_value=pool),
        patch(
            "src.pipelines.report_generation.pipeline.transcribe_inspection_audio_files",
            AsyncMock(),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.analyze_inspection_photo_files",
            AsyncMock(),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_transcription_segments_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch.object(
            ReportPipelineRepository,
            "fetch_image_analyses_for_inspection",
            AsyncMock(return_value=[]),
        ),
        patch(
            "src.pipelines.report_generation.pipeline.generate_report_sections",
            AsyncMock(side_effect=ValueError("bad")),
        ),
        patch.object(pipeline.queries, "set_report_status", AsyncMock()) as set_status,
    ):
        with pytest.raises(ValueError, match="bad"):
            await pipeline.run_report_generation("report-id")

    set_status.assert_awaited_once_with("report-id", "failed")
