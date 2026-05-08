import asyncpg

from src.config import settings
from src.models.reports.report import ReportSummary


def get_database_connection_url() -> str:
    return settings.database_url.replace("+asyncpg", "")


def map_report_summary(row: asyncpg.Record) -> ReportSummary:
    return ReportSummary(id=row["id"], company_id=row["company_id"], status=row["status"])


async def list_report_summaries_by_company_id(company_id: str) -> list[ReportSummary]:
    connection = await asyncpg.connect(get_database_connection_url())

    try:
        rows = await connection.fetch(
            """
            SELECT id, company_id, status
            FROM reports
            WHERE company_id = $1::uuid
            ORDER BY created_at DESC
            """,
            company_id,
        )
    finally:
        await connection.close()

    return [map_report_summary(row) for row in rows]
