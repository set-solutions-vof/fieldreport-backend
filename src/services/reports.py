from src.db import report_queries, template_queries
from src.db.report_mapper import map_report_detail_sections
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportEvidenceItem,
    ReportSection,
    ReportSummary,
)
from src.models.templates.domain import TemplateSection


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_queries.list_report_summaries_by_company_id(str(user.company_id))


async def load_report_detail_sections(
    report_id: str,
) -> tuple[list[ReportDetailSection], list[ReportEvidenceItem]]:
    rows = await report_queries.fetch_report_section_rows(report_id)

    return map_report_detail_sections(rows)


async def load_template_sections_by_id(company_id: str) -> dict[str, TemplateSection]:
    company_template = await template_queries.fetch_active_company_template(company_id)
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
    sections, evidence_items = await load_report_detail_sections(report_id)
    template_sections_by_id = await load_template_sections_by_id(str(user.company_id))
    sections = [apply_template_to_section(section, template_sections_by_id) for section in sections]

    return report.model_copy(update={"sections": sections, "evidence_items": evidence_items})


async def update_report_section(
    report_id: str,
    section_id: str,
    user: CurrentUser,
    reviewed_content: str | None,
    approved: bool | None,
) -> ReportSection:
    section = await report_queries.update_report_section(
        report_id,
        section_id,
        str(user.company_id),
        reviewed_content,
        approved,
    )
    template_sections_by_id = await load_template_sections_by_id(str(user.company_id))

    return apply_template_to_section(section, template_sections_by_id)
