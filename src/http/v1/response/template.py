from src.models.templates.configuration import (
    TemplateConfiguration,
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationFailed,
    TemplateConfigurationNotConfigured,
    TemplateConfigurationPendingReview,
)
from src.models.templates.state import TemplateCompanyState


def template_configuration_response(state: TemplateCompanyState) -> TemplateConfiguration:
    if state.view_status == "not_configured":
        return TemplateConfigurationNotConfigured(status="not_configured")

    if state.view_status == "extracting":
        return TemplateConfigurationExtracting(
            status="extracting",
            jobId=str(state.job_id),
            reports_count=state.reports_count,
        )

    if state.view_status == "pending_review":
        return TemplateConfigurationPendingReview(
            status="pending_review",
            job_id=str(state.job_id),
            reports_count=state.reports_count,
            sections=state.structure.sections,
        )

    if state.view_status == "failed":
        return TemplateConfigurationFailed(
            status="failed",
            reports_count=state.reports_count,
            error_message=state.error_message,
        )

    return TemplateConfigurationActive(
        status="active",
        reports_count=state.reports_count,
        sections=state.structure.sections,
    )
