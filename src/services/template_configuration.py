from src.models.templates.configuration import (
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationFailed,
    TemplateConfigurationNotConfigured,
    TemplateConfigurationPendingReview,
)
from src.models.templates.state import TemplateCompanyState


def build_template_configuration(
    state: TemplateCompanyState,
) -> (
    TemplateConfigurationNotConfigured
    | TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
):
    if state.view_status == "not_configured":
        return TemplateConfigurationNotConfigured(status="not_configured")

    if state.view_status == "extracting":
        return TemplateConfigurationExtracting(
            status="extracting",
            jobId=str(state.job_id) if state.job_id is not None else "",
            reports_count=state.reports_count,
        )

    if state.view_status == "pending_review":
        return TemplateConfigurationPendingReview(
            status="pending_review",
            reports_count=state.reports_count,
            sections=state.structure.sections if state.structure else [],
        )

    if state.view_status == "failed":
        return TemplateConfigurationFailed(
            status="failed",
            reports_count=state.reports_count,
            error_message=state.error_message or "Template analysis failed",
        )

    return TemplateConfigurationActive(
        status="active",
        reports_count=state.reports_count,
        sections=state.structure.sections if state.structure else [],
    )
