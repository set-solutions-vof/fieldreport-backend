from src.db.template_mapper import map_sections
from src.models.templates.template import (
    StoredTemplateStructure,
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationFailed,
    TemplateConfigurationPendingReview,
)


def build_template_configuration(
    status: str,
    reports_count: int,
    structure: StoredTemplateStructure | None,
    job_id: str | None = None,
    error_message: str | None = None,
) -> (
    TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
):
    if status in {"queued", "processing", "extracting"}:
        return TemplateConfigurationExtracting(
            status="extracting",
            jobId=job_id or "",
            reports_count=reports_count,
        )

    if status == "pending_review":
        return TemplateConfigurationPendingReview(
            status="pending_review",
            reports_count=reports_count,
            sections=map_sections(structure),
        )

    if status == "failed":
        return TemplateConfigurationFailed(
            status="failed",
            reports_count=reports_count,
            error_message=error_message or "Template analysis failed",
        )

    return TemplateConfigurationActive(
        status="active",
        reports_count=reports_count,
        sections=map_sections(structure),
    )
