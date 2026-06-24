from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
    TemplateStatusNotConfigured,
)
from src.models.templates.records import ActiveCompanyTemplateRecord


def build_template_status_active(
    active_template: ActiveCompanyTemplateRecord,
) -> TemplateStatusActive:
    return TemplateStatusActive(
        status="active",
        source_reports_count=active_template.source_reports_count,
        metadata_fields=active_template.structure.metadata_fields,
        sections=active_template.structure.sections,
        template_id=str(active_template.current_template_id),
        version=active_template.version,
        updated_at=active_template.created_at,
    )


def resolve_template_company_state(
    active_template: ActiveCompanyTemplateRecord | None,
) -> TemplateStatus:
    if active_template is not None:
        return build_template_status_active(active_template)

    return TemplateStatusNotConfigured(status="not_configured")
