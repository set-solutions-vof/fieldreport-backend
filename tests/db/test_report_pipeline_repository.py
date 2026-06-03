from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from src.db.report_pipeline_repository import ReportPipelineRepository
from src.models.reports.generation import GeneratedReportSection
from src.models.reports.transcription import TranscriptionSegment
from src.models.templates.domain import TemplateSection


def build_connection() -> SimpleNamespace:
    return SimpleNamespace(execute=AsyncMock())


async def test_insert_transcription_executes_insert_and_returns_id() -> None:
    connection = build_connection()
    repository = ReportPipelineRepository(connection)

    transcription_id = await repository.insert_transcription(
        "inspection-id",
        "company-id",
        "/tmp/audio.m4a",
        "Tekst",
        12.5,
    )

    assert transcription_id
    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-4:] == (
        "inspection-id",
        "company-id",
        "/tmp/audio.m4a",
        "Tekst",
    )


async def test_insert_transcription_segments_executes_inserts_and_returns_ids() -> None:
    connection = build_connection()
    repository = ReportPipelineRepository(connection)
    segments = [
        TranscriptionSegment(
            segment_index=0,
            start_seconds=0.0,
            end_seconds=1.5,
            text="Segment",
        )
    ]

    segment_ids = await repository.insert_transcription_segments(
        "transcription-id",
        "inspection-id",
        segments,
    )

    assert len(segment_ids) == 1
    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-4:] == (
        0,
        0.0,
        1.5,
        "Segment",
    )


async def test_insert_image_analysis_executes_insert_and_returns_id() -> None:
    connection = build_connection()
    repository = ReportPipelineRepository(connection)

    image_analysis_id = await repository.insert_image_analysis(
        "inspection-id",
        "company-id",
        "/tmp/photo.jpg",
        "Fotoanalyse",
    )

    assert image_analysis_id
    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-4:] == (
        "inspection-id",
        "company-id",
        "/tmp/photo.jpg",
        "Fotoanalyse",
    )


async def test_insert_report_section_executes_insert_and_returns_id() -> None:
    connection = build_connection()
    repository = ReportPipelineRepository(connection)
    section = GeneratedReportSection(
        id="conclusie",
        generated_content="Concept",
        confidence_level="high",
        confidence_score=0.9,
    )
    template_section = TemplateSection(
        id="conclusie",
        label="Conclusie",
        order=1,
        render_type="text_block",
    )

    report_section_id = await repository.insert_report_section(
        "report-id",
        "company-id",
        section,
        template_section,
    )

    assert report_section_id
    connection.execute.assert_awaited_once()
    assert "to_jsonb(ARRAY[$7::text])" in connection.execute.await_args.args[0]
    assert connection.execute.await_args.args[-6:] == (
        "conclusie",
        1,
        "text_block",
        "Concept",
        "high",
        0.9,
    )


async def test_insert_report_section_source_transcription_executes_insert() -> None:
    connection = build_connection()
    repository = ReportPipelineRepository(connection)

    await repository.insert_report_section_source_transcription(
        "section-id",
        "segment-id",
    )

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("section-id", "segment-id")


async def test_insert_report_section_source_image_executes_insert() -> None:
    connection = build_connection()
    repository = ReportPipelineRepository(connection)

    await repository.insert_report_section_source_image("section-id", "image-id")

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("section-id", "image-id")


async def test_fetch_transcription_segments_for_inspection_returns_mapped_rows() -> None:
    segment_id = uuid4()
    connection = SimpleNamespace(
        fetch=AsyncMock(
            return_value=[
                {
                    "id": segment_id,
                    "transcription_id": uuid4(),
                    "inspection_id": uuid4(),
                    "segment_index": 0,
                    "start_seconds": 0.0,
                    "end_seconds": 1.5,
                    "text": "Segment",
                    "created_at": None,
                }
            ]
        )
    )
    repository = ReportPipelineRepository(connection)

    segments = await repository.fetch_transcription_segments_for_inspection("inspection-id")

    assert len(segments) == 1
    assert segments[0].id == segment_id
    assert segments[0].text == "Segment"


async def test_fetch_image_analyses_for_inspection_returns_mapped_rows() -> None:
    image_id = uuid4()
    connection = SimpleNamespace(
        fetch=AsyncMock(
            return_value=[
                {
                    "id": image_id,
                    "inspection_id": uuid4(),
                    "company_id": uuid4(),
                    "storage_key": "/tmp/photo.jpg",
                    "analysis_text": "Fotoanalyse",
                    "captured_at": None,
                    "created_at": None,
                }
            ]
        )
    )
    repository = ReportPipelineRepository(connection)

    images = await repository.fetch_image_analyses_for_inspection("inspection-id")

    assert len(images) == 1
    assert images[0].id == image_id
    assert images[0].analysis_text == "Fotoanalyse"
