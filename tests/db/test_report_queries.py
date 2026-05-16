from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.db import report_queries
from src.db.report_mapper import map_report_detail_sections


class FakeConnection:
    def __init__(self, rows=None, row=None):
        self.rows = rows
        self.row = row
        self.fetch = AsyncMock(return_value=rows)
        self.fetchrow = AsyncMock(return_value=row)
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
            "section_key": "bevindingen",
            "section_order": 1,
            "ai_draft": "Draft text",
            "field_expert_content": None,
            "is_approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "source_type": "image_analysis",
            "transcription_segment_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "image_analysis_id": shared_image_analysis_id,
            "captured_at": capture_time,
            "image_analysis_text": "Thermal image",
            "timeline_offset_seconds": 20.0,
        },
        {
            "id": first_section_id,
            "section_key": "bevindingen",
            "section_order": 1,
            "ai_draft": "Draft text",
            "field_expert_content": None,
            "is_approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "source_type": "transcription_segment",
            "transcription_segment_id": shared_transcription_segment_id,
            "start_seconds": 12.0,
            "end_seconds": 15.0,
            "transcription_text": "Moisture mentioned",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_offset_seconds": 12.0,
        },
        {
            "id": second_section_id,
            "section_key": "advies",
            "section_order": 2,
            "ai_draft": "Advice",
            "field_expert_content": None,
            "is_approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "source_type": "transcription_segment",
            "transcription_segment_id": shared_transcription_segment_id,
            "start_seconds": 12.0,
            "end_seconds": 15.0,
            "transcription_text": "Moisture mentioned",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_offset_seconds": 12.0,
        },
        {
            "id": second_section_id,
            "section_key": "advies",
            "section_order": 2,
            "ai_draft": "Advice",
            "field_expert_content": None,
            "is_approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "source_type": "transcription_segment",
            "transcription_segment_id": first_unique_segment_id,
            "start_seconds": 5.0,
            "end_seconds": 8.0,
            "transcription_text": "Opening note",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_offset_seconds": 5.0,
        },
        {
            "id": second_section_id,
            "section_key": "advies",
            "section_order": 2,
            "ai_draft": "Advice",
            "field_expert_content": None,
            "is_approved": False,
            "confidence_level": "medium",
            "confidence_score": 0.71,
            "source_type": "image_analysis",
            "transcription_segment_id": None,
            "start_seconds": None,
            "end_seconds": None,
            "transcription_text": None,
            "image_analysis_id": shared_image_analysis_id,
            "captured_at": capture_time,
            "image_analysis_text": "Thermal image",
            "timeline_offset_seconds": 20.0,
        },
        {
            "id": third_section_id,
            "section_key": "samenvatting",
            "section_order": 3,
            "ai_draft": "Summary",
            "field_expert_content": None,
            "is_approved": False,
            "confidence_level": "low",
            "confidence_score": 0.42,
            "source_type": "transcription_segment",
            "transcription_segment_id": third_section_segment_id,
            "start_seconds": 30.0,
            "end_seconds": 35.0,
            "transcription_text": "Summary audio",
            "image_analysis_id": None,
            "captured_at": None,
            "image_analysis_text": None,
            "timeline_offset_seconds": 30.0,
        },
    ]
    connection = FakeConnection(rows)

    with patch(
        "src.db.report_queries.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        rows = await report_queries.fetch_report_section_rows(str(uuid4()))
        sections, timeline_items = map_report_detail_sections(rows)

    assert [section.id for section in sections] == [
        first_section_id,
        second_section_id,
        third_section_id,
    ]
    assert sections[0].source_item_ids == [
        shared_image_analysis_id,
        shared_transcription_segment_id,
    ]
    assert sections[1].source_item_ids == [
        shared_transcription_segment_id,
        first_unique_segment_id,
        shared_image_analysis_id,
    ]
    assert sections[2].source_item_ids == [third_section_segment_id]
    assert [timeline_item.id for timeline_item in timeline_items] == [
        first_unique_segment_id,
        shared_transcription_segment_id,
        shared_image_analysis_id,
        third_section_segment_id,
    ]
    assert [timeline_item.source_type for timeline_item in timeline_items] == [
        "transcription_segment",
        "transcription_segment",
        "image_analysis",
        "transcription_segment",
    ]
    assert [timeline_item.timeline_offset_seconds for timeline_item in timeline_items] == [
        5.0,
        12.0,
        20.0,
        30.0,
    ]
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_update_report_section_returns_updated_section_for_company() -> None:
    report_id = uuid4()
    section_id = uuid4()
    company_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 45, tzinfo=UTC)
    rows = [
        {
            "id": section_id,
            "section_key": "advies",
            "section_order": 2,
            "ai_draft": "Advice",
            "field_expert_content": "Updated advice",
            "is_approved": True,
            "confidence_level": "low",
            "confidence_score": 0.32,
            "source_type": "image_analysis",
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
    assert section.section_key == "advies"
    assert section.field_expert_content == "Updated advice"
    assert section.is_approved is True
    assert section.confidence_level == "low"
    assert section.confidence_score == 0.32
    assert section.sources[0].type == "image"
    assert section.sources[0].capture_time == capture_time
    assert section.sources[0].content_summary == "Image summary"
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
            "section_key": "advies",
            "section_order": 2,
            "ai_draft": "Advice",
            "field_expert_content": "Expert advice",
            "is_approved": False,
            "confidence_level": "high",
            "confidence_score": 0.95,
            "source_type": "transcription_segment",
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
    assert section.field_expert_content == "Expert advice"
    assert section.is_approved is False
    assert section.sources[0].type == "audio"
    connection.fetchrow.assert_awaited_once()
    assert "SELECT report_sections.id" in connection.fetchrow.await_args.args[0]
    assert connection.fetchrow.await_args.args[1:] == (
        str(report_id),
        str(section_id),
        str(company_id),
    )
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()
