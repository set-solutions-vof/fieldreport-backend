from src.db import report_queries, template_queries
from src.db.report_mapper import map_report_detail_sections
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSummary,
)
from src.models.templates.domain import TemplateSection


async def get_report_detail(report_id: str, user: CurrentUser) -> ReportDetail:
    company_id = str(user.company_id)
    report = await report_queries.get_report_by_id(report_id, company_id)
    sections, evidence_items = map_report_detail_sections(
        await report_queries.fetch_report_section_rows(report_id, company_id)
    )
    company_template = await template_queries.fetch_active_company_template(company_id)
    sections_by_id = {
        template_section.id: template_section
        for template_section in company_template.structure.sections
    }
    sections = [
        apply_template_section(section, sections_by_id[section.section_id]) for section in sections
    ]

    return report.model_copy(update={"sections": sections, "evidence_items": evidence_items})


async def update_report_section(
    report_id: str,
    section_id: str,
    user: CurrentUser,
    reviewed_content: str | None,
    approved: bool | None,
) -> ReportSection:
    company_id = str(user.company_id)
    section = await report_queries.update_report_section(
        report_id,
        section_id,
        company_id,
        reviewed_content,
        approved,
    )
    company_template = await template_queries.fetch_active_company_template(company_id)
    template_section = next(
        template_section
        for template_section in company_template.structure.sections
        if template_section.id == section.section_id
    )

    return apply_template_section(section, template_section)


async def list_reports_for_user(user: CurrentUser) -> list[ReportSummary]:
    return await report_queries.list_report_summaries_by_company_id(str(user.company_id))


def apply_template_section[SectionT: ReportSection | ReportDetailSection](
    section: SectionT, template_section: TemplateSection
) -> SectionT:
    return section.model_copy(
        update={
            "label": template_section.label,
            "fields": template_section.fields,
            "groups": template_section.groups,
        }
    )
