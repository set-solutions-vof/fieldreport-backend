from src.db import report_queries
from src.db.report_mapper import map_report_detail_sections
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSummary,
    ReportTimelineItem,
)


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_queries.list_report_summaries_by_company_id(str(user.company_id))


async def load_report_detail_sections(
    report_id: str,
) -> tuple[list[ReportDetailSection], list[ReportTimelineItem]]:
    rows = await report_queries.fetch_report_section_rows(report_id)

    return map_report_detail_sections(rows)


async def get_report_detail(report_id: str, user: CurrentUser) -> ReportDetail:
    report = await report_queries.get_report_by_id(report_id, str(user.company_id))
    sections, timeline_items = await load_report_detail_sections(report_id)

    return report.model_copy(update={"sections": sections, "timeline_items": timeline_items})


async def update_report_section(
    report_id: str,
    section_id: str,
    user: CurrentUser,
    field_expert_content: str | None,
    is_approved: bool | None,
) -> ReportSection:
    return await report_queries.update_report_section(
        report_id,
        section_id,
        str(user.company_id),
        field_expert_content,
        is_approved,
    )
