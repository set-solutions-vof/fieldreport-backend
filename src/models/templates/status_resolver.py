from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
    TemplateStatusFailed,
    TemplateStatusNotConfigured,
    TemplateStatusPendingReview,
    TemplateStatusProcessing,
)
from src.models.templates.records import ActiveCompanyTemplateRecord, TemplateAnalysisJobRecord


def resolve_template_company_state(
    active_template: ActiveCompanyTemplateRecord | None,
    job: TemplateAnalysisJobRecord | None,
) -> TemplateStatus:
    if job is not None and job.status in {
        "queued",
        "processing",
        "pending_review",
        "failed",
    }:
        return resolve_template_job_state(job)

    if active_template is not None:
        return TemplateStatusActive(
            status="active",
            source_reports_count=0,
            metadata_fields=active_template.structure.metadata_fields,
            sections=active_template.structure.sections,
        )

    return TemplateStatusNotConfigured(status="not_configured")


def resolve_template_job_state(job: TemplateAnalysisJobRecord) -> TemplateStatus:
    if job.status in {"queued", "processing"}:
        return TemplateStatusProcessing(
            status="processing",
            job_id=str(job.id),
            source_reports_count=job.source_reports_count,
        )

    if job.status == "pending_review":
        return TemplateStatusPendingReview(
            status="pending_review",
            job_id=str(job.id),
            source_reports_count=job.source_reports_count,
            metadata_fields=job.structure.metadata_fields,
            sections=job.structure.sections,
        )

    if job.status == "failed":
        return TemplateStatusFailed(
            status="failed",
            source_reports_count=job.source_reports_count,
            failure_message=job.failure_message,
        )

    return TemplateStatusActive(
        status="active",
        source_reports_count=job.source_reports_count,
        metadata_fields=job.structure.metadata_fields,
        sections=job.structure.sections,
    )
