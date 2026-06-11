from src.db.report import queries
from src.db.report.mapper import map_report_detail_sections
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSummary,
)


async def get_report_detail(report_id: str, user: CurrentUser) -> ReportDetail:
    company_id = str(user.company_id)
    report = await queries.get_report_by_id(report_id, company_id)
    sections, evidence_items = map_report_detail_sections(
        await queries.fetch_report_section_rows(report_id, company_id)
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
    return await queries.update_report_section(
        report_id,
        section_id,
        company_id,
        reviewed_content,
        approved,
    )


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await queries.list_report_summaries_by_company_id(str(user.company_id))


async def retry_failed_report(report_id: str, user: CurrentUser) -> None:
    company_id = str(user.company_id)
    report = await queries.get_report_by_id(report_id, company_id)

    if report.status != "failed":
        raise ValueError("Report retry is only allowed for failed reports")

    await queries.reset_report_for_retry(report_id, company_id)
