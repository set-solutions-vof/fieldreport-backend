from src.db import report_queries
from src.db.report_mapper import map_report_detail_sections
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSummary,
)


async def get_report_detail(report_id: str, user: CurrentUser) -> ReportDetail:
    company_id = str(user.company_id)
    report = await report_queries.get_report_by_id(report_id, company_id)
    sections, evidence_items = map_report_detail_sections(
        await report_queries.fetch_report_section_rows(report_id, company_id)
    )
    return report.model_copy(update={"sections": sections, "evidence_items": evidence_items})


async def update_report_section(
    report_id: str,
    section_id: str,
    user: CurrentUser,
    reviewed_content: str | None,
    approved: bool | None,
) -> ReportSection:
    company_id = str(user.company_id)
    return await report_queries.update_report_section(
        report_id,
        section_id,
        company_id,
        reviewed_content,
        approved,
    )


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_queries.list_report_summaries_by_company_id(str(user.company_id))
