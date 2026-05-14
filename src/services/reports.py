from src.db import report_repository
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import ReportDetail, ReportSection, ReportSummary


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_repository.list_report_summaries_by_company_id(str(user.company_id))


async def get_report_detail(report_id: str, user: CurrentUser) -> ReportDetail:
    report = await report_repository.get_report_by_id(report_id, str(user.company_id))
    sections, timeline_items = await report_repository.get_report_detail_sections(report_id)

    return report.model_copy(update={"sections": sections, "timeline_items": timeline_items})


async def update_report_section(
    report_id: str,
    section_id: str,
    user: CurrentUser,
    field_expert_content: str | None,
    is_approved: bool | None,
) -> ReportSection:
    return await report_repository.update_report_section(
        report_id,
        section_id,
        str(user.company_id),
        field_expert_content,
        is_approved,
    )
