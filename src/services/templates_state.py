from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
    TemplateStatusFailed,
    TemplateStatusNotConfigured,
    TemplateStatusPendingReview,
    TemplateStatusProcessing,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord, TemplateAnalysisJobRecord


def resolve_template_company_state(
    active_template: ActiveCompanyTemplateRecord | None,
    job: TemplateAnalysisJobRecord | None,
) -> TemplateStatus:
    if job is not None and job.status in {"queued", "processing", "pending_review"}:
        return resolve_template_job_state(job)

    if active_template is not None:
        source_reports_count = (
            job.source_reports_count if job is not None and job.status == "active" else 0
        )
        return _active_state(active_template.structure, source_reports_count)

    if job is not None and job.status == "failed":
        return _failed_state(job)

    return TemplateStatusNotConfigured(status="not_configured")


def resolve_template_job_state(job: TemplateAnalysisJobRecord) -> TemplateStatus:
    if job.status in {"queued", "processing"}:
        return _processing_state(job)

    if job.status == "pending_review":
        return _pending_review_state(job)

    if job.status == "failed":
        return _failed_state(job)

    return _active_state(job.structure, job.source_reports_count)


def _processing_state(job: TemplateAnalysisJobRecord) -> TemplateStatusProcessing:
    return TemplateStatusProcessing(
        status="processing",
        job_id=str(job.id),
        source_reports_count=job.source_reports_count,
    )


def _pending_review_state(job: TemplateAnalysisJobRecord) -> TemplateStatusPendingReview:
    return TemplateStatusPendingReview(
        status="pending_review",
        job_id=str(job.id),
        source_reports_count=job.source_reports_count,
        sections=job.structure.sections,
    )


def _failed_state(job: TemplateAnalysisJobRecord) -> TemplateStatusFailed:
    return TemplateStatusFailed(
        status="failed",
        source_reports_count=job.source_reports_count,
        failure_message=job.failure_message,
    )


def _active_state(
    structure: TemplateStructure,
    source_reports_count: int,
) -> TemplateStatusActive:
    return TemplateStatusActive(
        status="active",
        source_reports_count=source_reports_count,
        sections=structure.sections,
    )
