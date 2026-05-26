from typing import TypeGuard

from src.models.templates.configuration import (
    TemplateConfiguration,
    TemplateConfigurationActive,
    TemplateConfigurationFailed,
    TemplateConfigurationNotConfigured,
    TemplateConfigurationPendingReview,
    TemplateConfigurationProcessing,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord


def resolve_template_company_state(
    company: CompanyTemplateRecord,
    job: TemplateAnalysisJobRecord | None,
) -> TemplateConfiguration:
    if _is_unfinished_job(job):
        return resolve_template_job_state(job)

    if company.template_id is not None:
        return _active_state(company.structure, _active_template_reports_count(job))

    if job is not None and job.status == "failed":
        return _failed_state(job)

    return TemplateConfigurationNotConfigured(status="not_configured")


def resolve_template_job_state(job: TemplateAnalysisJobRecord) -> TemplateConfiguration:
    if job.status in {"queued", "processing"}:
        return _processing_state(job)

    if job.status == "pending_review":
        return _pending_review_state(job)

    if job.status == "failed":
        return _failed_state(job)

    return _active_state(job.structure, job.reports_count)


def _processing_state(job: TemplateAnalysisJobRecord) -> TemplateConfigurationProcessing:
    return TemplateConfigurationProcessing(
        status="processing",
        job_id=str(job.id),
        reports_count=job.reports_count,
    )


def _pending_review_state(job: TemplateAnalysisJobRecord) -> TemplateConfigurationPendingReview:
    return TemplateConfigurationPendingReview(
        status="pending_review",
        job_id=str(job.id),
        reports_count=job.reports_count,
        sections=job.structure.sections,
    )


def _failed_state(job: TemplateAnalysisJobRecord) -> TemplateConfigurationFailed:
    return TemplateConfigurationFailed(
        status="failed",
        reports_count=job.reports_count,
        error_message=job.error_message,
    )


def _active_state(
    structure: TemplateStructure,
    reports_count: int,
) -> TemplateConfigurationActive:
    return TemplateConfigurationActive(
        status="active",
        reports_count=reports_count,
        sections=structure.sections,
    )


def _is_unfinished_job(
    job: TemplateAnalysisJobRecord | None,
) -> TypeGuard[TemplateAnalysisJobRecord]:
    return job is not None and job.status in {"queued", "processing", "pending_review"}


def _active_template_reports_count(job: TemplateAnalysisJobRecord | None) -> int:
    if job is None or job.status != "active":
        return 0

    return job.reports_count
