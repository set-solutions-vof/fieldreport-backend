from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.integrations import report_repository


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

    with (
        patch.object(
            report_repository.settings,
            "database_url",
            "postgresql+asyncpg://fieldreport:fieldreport@localhost:5432/fieldreport_test",
        ),
        patch(
            "src.integrations.report_repository.asyncpg.connect",
            AsyncMock(return_value=connection),
        ),
    ):
        reports = await report_repository.list_report_summaries_by_company_id(str(company_id))

        assert (
            report_repository.get_database_connection_url()
            == "postgresql://fieldreport:fieldreport@localhost:5432/fieldreport_test"
        )

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
    row = {
        "id": report_id,
        "status": "draft",
        "client_name": "ACME",
        "address": "Main Street 1",
        "inspection_date": inspection_date,
        "inspector_name": "Jeroen van Dijk",
    }
    connection = FakeConnection(row=row)

    with patch(
        "src.integrations.report_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        report = await report_repository.get_report_by_id(str(report_id), str(company_id))

    assert report is not None
    assert report.id == report_id
    assert report.status == "draft"
    assert report.client_name == "ACME"
    assert report.address == "Main Street 1"
    assert report.inspection_date == inspection_date
    assert report.inspector_name == "Jeroen van Dijk"
    assert report.sections == []
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_report_by_id_returns_none_when_report_is_missing() -> None:
    connection = FakeConnection(row=None)

    with patch(
        "src.integrations.report_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        report = await report_repository.get_report_by_id(str(uuid4()), str(uuid4()))

    assert report is None
    connection.fetchrow.assert_awaited_once()
    connection.close.assert_awaited_once()


async def test_get_sections_with_sources_returns_ordered_sections() -> None:
    first_section_id = uuid4()
    second_section_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 45, tzinfo=UTC)
    rows = [
        {
            "id": first_section_id,
            "section_key": "bevindingen",
            "section_order": 1,
            "ai_draft": "Draft text",
            "field_expert_content": None,
            "is_approved": False,
            "source_type": "transcription_segment",
            "timestamp_start": 1.5,
            "timestamp_end": 4.0,
            "transcription_text": "Audio summary",
            "capture_time": None,
            "image_analysis_text": None,
        },
        {
            "id": first_section_id,
            "section_key": "bevindingen",
            "section_order": 1,
            "ai_draft": "Draft text",
            "field_expert_content": None,
            "is_approved": False,
            "source_type": "image_analysis",
            "timestamp_start": None,
            "timestamp_end": None,
            "transcription_text": None,
            "capture_time": capture_time,
            "image_analysis_text": "Image summary",
        },
        {
            "id": second_section_id,
            "section_key": "advies",
            "section_order": 2,
            "ai_draft": "Advice",
            "field_expert_content": "Expert advice",
            "is_approved": True,
            "source_type": None,
            "timestamp_start": None,
            "timestamp_end": None,
            "transcription_text": None,
            "capture_time": None,
            "image_analysis_text": None,
        },
    ]
    connection = FakeConnection(rows)

    with patch(
        "src.integrations.report_repository.asyncpg.connect",
        AsyncMock(return_value=connection),
    ):
        sections = await report_repository.get_sections_with_sources(str(uuid4()))

    assert [section.id for section in sections] == [first_section_id, second_section_id]
    assert sections[0].section_key == "bevindingen"
    assert sections[0].sources[0].type == "audio"
    assert sections[0].sources[0].timestamp_start == 1.5
    assert sections[0].sources[0].timestamp_end == 4.0
    assert sections[0].sources[0].content_summary == "Audio summary"
    assert sections[0].sources[1].type == "image"
    assert sections[0].sources[1].capture_time == capture_time
    assert sections[0].sources[1].content_summary == "Image summary"
    assert sections[1].sources == []
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()
