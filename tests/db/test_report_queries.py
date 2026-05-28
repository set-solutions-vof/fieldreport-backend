from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import report_queries
from src.db.report_mapper import map_report_detail_sections
from src.models.reports.transcription import TranscriptionSegment


class FakeConnection:
    def __init__(self, rows=None, row=None):
        self.rows = rows
        self.row = row
        self.fetch = AsyncMock(return_value=rows)
        self.fetchrow = AsyncMock(return_value=row)
        self.execute = AsyncMock()
        self.close = AsyncMock()


async def test_list_report_summaries_by_company_id_returns_mapped_reports() -> None:
    company_id = uuid4()
    inspection_date = datetime(2026, 5, 8, 12, 30, tzinfo=UTC)
    rows = [
        {
            "id": uuid4(),
            "company_id": company_id,
            "status": "draft",
            "client_name": "ACME",
            "address": "Main Street 1",
            "inspection_date": inspection_date,
            "inspector_name": "Jeroen van Dijk",
        },
        {
            "id": uuid4(),
            "company_id": company_id,
            "status": "approved",
            "client_name": "Globex",
            "address": "Second Street 2",
            "inspection_date": inspection_date,
            "inspector_name": "Sanne de Vries",
        },
    ]
    connection = FakeConnection(rows)

    with patch(
        "src.db.report_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        reports = await report_queries.list_report_summaries_by_company_id(str(company_id))

    assert [report.id for report in reports] == [rows[0]["id"], rows[1]["id"]]
    assert all(report.company_id == company_id for report in reports)
    assert [report.status for report in reports] == ["draft", "approved"]
    assert [report.client_name for report in reports] == ["ACME", "Globex"]
    assert reports[0].address == "Main Street 1"
    assert reports[0].inspection_date == inspection_date
    assert reports[0].inspector_name == "Jeroen van Dijk"
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_report_by_id_returns_mapped_report_for_company() -> None:
    report_id = uuid4()
    company_id = uuid4()
    inspection_date = datetime(2026, 5, 8, 12, 30, tzinfo=UTC)
    updated_at = datetime(2026, 5, 9, 8, 15, tzinfo=UTC)
    row = {
        "id": report_id,
        "status": "draft",
        "client_name": "ACME",
        "address": "Main Street 1",
        "inspection_date": inspection_date,
        "inspector_name": "Jeroen van Dijk",
        "updated_at": updated_at,
    }
    connection = FakeConnection(row=row)

    with patch(
        "src.db.report_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        report = await report_queries.get_report_by_id(str(report_id), str(company_id))

    assert report is not None
    assert report.id == report_id
    assert report.status == "draft"
    assert report.client_name == "ACME"
    assert report.address == "Main Street 1"
    assert report.inspection_date == inspection_date
    assert report.inspector_name == "Jeroen van Dijk"
    assert report.updated_at == updated_at
    assert report.sections == []
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_fetch_report_section_rows_maps_detail_sections_and_timeline() -> None:
    first_section_id = uuid4()
    second_section_id = uuid4()
    third_section_id = uuid4()
    shared_transcription_segment_id = uuid4()
    first_unique_segment_id = uuid4()
    shared_image_analysis_id = uuid4()
    third_section_segment_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 30, 20, tzinfo=UTC)
    rows = [
        {
            "id": first_section_id,
            "section_id": "bevindingen",
            "section_order": 1,
            "generated_content": "Draft text",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "image_analysis",
            "transcription_segment_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "image_analysis_id": shared_image_analysis_id,
            "captured_at": capture_time,
            "image_analysis_text": "Thermal image",
            "timeline_seconds": 20.0,
        },
        {
            "id": first_section_id,
            "section_id": "bevindingen",
            "section_order": 1,
            "generated_content": "Draft text",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": shared_transcription_segment_id,
            "start_seconds": 12.0,
            "end_seconds": 15.0,
            "transcription_text": "Moisture mentioned",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 12.0,
        },
        {
            "id": second_section_id,
            "section_id": "advies",
            "section_order": 2,
            "generated_content": "Advice",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": shared_transcription_segment_id,
            "start_seconds": 12.0,
            "end_seconds": 15.0,
            "transcription_text": "Moisture mentioned",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 12.0,
        },
        {
            "id": second_section_id,
            "section_id": "advies",
            "section_order": 2,
            "generated_content": "Advice",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": first_unique_segment_id,
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "transcription_text": "Opening note",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 5.0,
        },
        {
            "id": second_section_id,
            "section_id": "advies",
            "section_order": 2,
            "generated_content": "Advice",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "evidence_type": "image_analysis",
            "transcription_segment_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "image_analysis_id": shared_image_analysis_id,
            "captured_at": capture_time,
            "image_analysis_text": "Thermal image",
            "timeline_seconds": 20.0,
        },
        {
            "id": third_section_id,
            "section_id": "samenvatting",
            "section_order": 3,
            "generated_content": "Summary",
            "reviewed_content": None,
            "approved": False,
            "confidence_level": "low",
            "confidence_score": 0.42,
            "evidence_type": "transcription_segment",
            "transcription_segment_id": third_section_segment_id,
            "start_seconds": 30.0,
            "end_seconds": 35.0,
            "transcription_text": "Summary audio",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_seconds": 30.0,
        },
    ]
    for row in rows:
        row["render_type"] = "text_block"
    rows[0]["render_type"] = "measurement_table"
    connection = FakeConnection(rows)

    with patch(
        "src.db.report_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        rows = await report_queries.fetch_report_section_rows(str(uuid4()))
        sections, evidence_items = map_report_detail_sections(rows)

    assert [section.id for section in sections] == [
        first_section_id,
        second_section_id,
        third_section_id,
    ]
    assert sections[0].render_type == "measurement_table"
    assert sections[0].evidence_item_ids == [
        shared_image_analysis_id,
        shared_transcription_segment_id,
    ]
    assert sections[1].evidence_item_ids == [
        shared_transcription_segment_id,
        first_unique_segment_id,
        shared_image_analysis_id,
    ]
    assert sections[2].evidence_item_ids == [third_section_segment_id]
    assert [evidence_item.id for evidence_item in evidence_items] == [
        first_unique_segment_id,
        shared_transcription_segment_id,
        shared_image_analysis_id,
        third_section_segment_id,
    ]
    assert [evidence_item.evidence_type for evidence_item in evidence_items] == [
        "transcription_segment",
        "transcription_segment",
        "image_analysis",
        "transcription_segment",
    ]
    assert [evidence_item.timeline_seconds for evidence_item in evidence_items] == [
        5.0,
        12.0,
        20.0,
        30.0,
    ]


async def test_claim_next_audio_pipeline_report_returns_claimed_report() -> None:
    row = {
        "id": uuid4(),
        "inspection_id": uuid4(),
        "company_id": uuid4(),
        "template_id": uuid4(),
    }
    connection = FakeConnection(row=row)

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        result = await report_queries.claim_next_audio_pipeline_report()

    assert result == row
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_report_for_pipeline_returns_report_context() -> None:
    from src.models.reports.pipeline import ReportPipelineContext

    row = {
        "id": uuid4(),
        "inspection_id": uuid4(),
        "company_id": uuid4(),
        "template_id": uuid4(),
        "status": "generating",
        "extra_context": "",
        "investigation_type": "Lekdetectie",
        "client_type": "Zakelijk",
    }
    connection = FakeConnection(row=row)

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        result = await report_queries.get_report_for_pipeline(str(row["id"]))

    assert result == ReportPipelineContext(**row)
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_set_report_status_executes_update() -> None:
    connection = FakeConnection()

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await report_queries.set_report_status("report-id", "draft")

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("report-id", "draft")
    connection.close.assert_awaited_once()


async def test_insert_transcription_executes_insert_and_returns_id() -> None:
    connection = FakeConnection()

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        transcription_id = await report_queries.insert_transcription(
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
    connection.close.assert_awaited_once()


async def test_insert_transcription_segments_executes_inserts_and_returns_ids() -> None:
    connection = FakeConnection()
    segments = [
        TranscriptionSegment(
            segment_index=0,
            start_seconds=0.0,
            end_seconds=1.5,
            text="Segment",
        )
    ]

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        segment_ids = await report_queries.insert_transcription_segments(
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
    connection.close.assert_awaited_once()


async def test_fetch_transcription_segments_for_inspection_returns_rows() -> None:
    from src.models.reports.pipeline import StoredTranscriptionSegment

    segment_id = uuid4()
    rows = [{"id": segment_id, "text": "Segment"}]
    connection = FakeConnection(rows=rows)

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        result = await report_queries.fetch_transcription_segments_for_inspection("inspection-id")

    assert result == [StoredTranscriptionSegment(id=segment_id, text="Segment")]
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_insert_image_analysis_executes_insert_and_returns_id() -> None:
    connection = FakeConnection()

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        image_analysis_id = await report_queries.insert_image_analysis(
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
    connection.close.assert_awaited_once()


async def test_fetch_image_analyses_for_inspection_returns_rows() -> None:
    from src.models.reports.pipeline import StoredImageAnalysis

    image_id = uuid4()
    rows = [{"id": image_id, "analysis_text": "Fotoanalyse"}]
    connection = FakeConnection(rows=rows)

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        result = await report_queries.fetch_image_analyses_for_inspection("inspection-id")

    assert result == [StoredImageAnalysis(id=image_id, analysis_text="Fotoanalyse")]
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_insert_report_section_executes_insert_and_returns_id() -> None:
    connection = FakeConnection()

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        report_section_id = await report_queries.insert_report_section(
            "report-id",
            "company-id",
            "conclusie",
            1,
            "text_block",
            "Concept",
            "high",
            0.9,
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
    connection.close.assert_awaited_once()


async def test_insert_report_section_source_transcription_executes_insert() -> None:
    connection = FakeConnection()

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await report_queries.insert_report_section_source_transcription(
            "section-id",
            "segment-id",
        )

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("section-id", "segment-id")
    connection.close.assert_awaited_once()


async def test_insert_report_section_source_image_executes_insert() -> None:
    connection = FakeConnection()

    with patch("src.db.report_queries.asyncpg.connect", AsyncMock(return_value=connection)):
        await report_queries.insert_report_section_source_image("section-id", "image-id")

    connection.execute.assert_awaited_once()
    assert connection.execute.await_args.args[-2:] == ("section-id", "image-id")
    connection.close.assert_awaited_once()


async def test_update_report_section_returns_updated_section_for_company() -> None:
    report_id = uuid4()
    section_id = uuid4()
    company_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 45, tzinfo=UTC)
    rows = [
        {
            "id": section_id,
            "section_id": "advies",
            "section_order": 2,
            "render_type": "key_value_table",
            "generated_content": "Advice",
            "reviewed_content": "Updated advice",
            "approved": True,
            "confidence_level": "low",
            "confidence_score": 0.32,
            "evidence_type": "image_analysis",
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "captured_at": capture_time,
            "image_analysis_text": "Image summary",
        }
    ]
    connection = FakeConnection(rows, {"id": section_id})

    with patch(
        "src.db.report_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        section = await report_queries.update_report_section(
            str(report_id),
            str(section_id),
            str(company_id),
            "Updated advice",
            True,
        )

    assert section is not None
    assert section.id == section_id
    assert section.section_id == "advies"
    assert section.render_type == "key_value_table"
    assert section.reviewed_content == "Updated advice"
    assert section.approved is True
    assert section.confidence_level == "low"
    assert section.confidence_score == 0.32
    assert section.evidence_sources[0].type == "image"
    assert section.evidence_sources[0].captured_at == capture_time
    assert section.evidence_sources[0].content_summary == "Image summary"
    connection.fetch.assert_awaited_once()
    connection.fetchrow.assert_awaited_once()
    assert connection.fetchrow.await_args.args[1:] == (
        str(report_id),
        str(section_id),
        str(company_id),
        "Updated advice",
        True,
    )
    assert connection.fetch.await_args.args[1:] == (section_id,)
    connection.close.assert_awaited_once()


async def test_update_report_section_returns_section_when_no_fields_are_changed() -> None:
    report_id = uuid4()
    section_id = uuid4()
    company_id = uuid4()
    rows = [
        {
            "id": section_id,
            "section_id": "advies",
            "section_order": 2,
            "label": "Advies",
            "render_type": "text_block",
            "fields": None,
            "groups": None,
            "generated_content": "Advice",
            "reviewed_content": "Expert advice",
            "approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "evidence_type": "transcription_segment",
            "start_seconds": 2.0,
            "end_seconds": 4.0,
            "transcription_text": "Advice audio",
            "captured_at": None,
            "image_analysis_text": None,
        }
    ]
    connection = FakeConnection(rows, {"id": section_id})

    with patch(
        "src.db.report_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        section = await report_queries.update_report_section(
            str(report_id),
            str(section_id),
            str(company_id),
            None,
            None,
        )

    assert section is not None
    assert section.id == section_id
    assert section.reviewed_content == "Expert advice"
    assert section.approved is False
    assert section.evidence_sources[0].type == "audio"
    connection.fetchrow.assert_awaited_once()
    assert "SELECT report_sections.id" in connection.fetchrow.await_args.args[0]
    assert connection.fetchrow.await_args.args[1:] == (
        str(report_id),
        str(section_id),
        str(company_id),
    )
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()
