from src.db import report_queries, template_queries
from src.db.report_mapper import map_report_detail_sections
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSummary,
    ReportTimelineItem,
)
from src.models.templates.configuration import TemplateSection


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_queries.list_report_summaries_by_company_id(str(user.company_id))


async def load_report_detail_sections(
    report_id: str,
) -> tuple[list[ReportDetailSection], list[ReportTimelineItem]]:
    rows = await report_queries.fetch_report_section_rows(report_id)

    return map_report_detail_sections(rows)


async def load_template_sections_by_id(company_id: str) -> dict[str, TemplateSection]:
    company_template, _ = await template_queries.fetch_company_template_context(company_id)
    return {section.id: section for section in company_template.structure.sections}


def apply_template_to_section[ReportSectionType: (ReportSection, ReportDetailSection)](
    section: ReportSectionType,
    template_sections_by_id: dict[str, TemplateSection],
) -> ReportSectionType:
    template_section = template_sections_by_id[section.section_id]
    return section.model_copy(
        update={
            "label": template_section.label,
            "fields": template_section.fields,
            "groups": template_section.groups,
        }
    )


async def get_report_detail(report_id: str, user: CurrentUser) -> ReportDetail:
    report = await report_queries.get_report_by_id(report_id, str(user.company_id))
    sections, timeline_items = await load_report_detail_sections(report_id)
    template_sections_by_id = await load_template_sections_by_id(str(user.company_id))
    sections = [apply_template_to_section(section, template_sections_by_id) for section in sections]

    return report.model_copy(update={"sections": sections, "timeline_items": timeline_items})


async def update_report_section(
    report_id: str,
    section_id: str,
    user: CurrentUser,
    field_expert_content: str | None,
    is_approved: bool | None,
) -> ReportSection:
    section = await report_queries.update_report_section(
        report_id,
        section_id,
        str(user.company_id),
        field_expert_content,
        is_approved,
    )
    template_sections_by_id = await load_template_sections_by_id(str(user.company_id))

    return apply_template_to_section(section, template_sections_by_id)
