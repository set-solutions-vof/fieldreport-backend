from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.integrations import report_repository


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.fetch = AsyncMock(return_value=rows)
        self.close = AsyncMock()


async def test_list_report_summaries_by_company_id_returns_mapped_reports() -> None:
    company_id = uuid4()
    rows = [
        {"id": uuid4(), "company_id": company_id, "status": "draft"},
        {"id": uuid4(), "company_id": company_id, "status": "approved"},
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
    connection.fetch.assert_awaited_once()
    connection.close.assert_awaited_once()
