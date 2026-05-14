from uuid import uuid4

from fastapi import UploadFile

from src.db import template_repository
from src.db.template_mapper import build_structure
from src.models.auth.authentication import CurrentUser
from src.models.templates.template import (
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationFailed,
    TemplateConfigurationNotConfigured,
    TemplateConfigurationPendingReview,
    TemplateSection,
)
from src.services.template_configuration import build_template_configuration
from src.storage import template_file_storage


async def get_template_configuration(
    user: CurrentUser,
) -> (
    TemplateConfigurationNotConfigured
    | TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
):
    company_id = str(user.company_id)
    company_row, job_row = await template_repository.get_company_template_context(company_id)

    if job_row is not None:
        return build_template_configuration(
            job_row.status,
            job_row.reports_count,
            job_row.structure,
            str(job_row.id),
            job_row.error_message,
        )

    if company_row.active_template_id is not None:
        return build_template_configuration("active", 0, company_row.active_structure)

    return TemplateConfigurationNotConfigured(status="not_configured")


async def start_template_analysis(
    user: CurrentUser,
    files: list[UploadFile],
) -> TemplateConfigurationExtracting:
    company_id = str(user.company_id)
    job_id = str(uuid4())
    stored_files = await template_file_storage.store_template_analysis_files(
        company_id,
        job_id,
        files,
    )

    await template_repository.replace_template_analysis_job(job_id, company_id, stored_files)

    return TemplateConfigurationExtracting(
        status="extracting",
        jobId=job_id,
        reports_count=len(files),
    )


async def get_template_analysis(
    user: CurrentUser,
    job_id: str,
) -> (
    TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
):
    job_row = await template_repository.get_template_analysis_job(job_id, str(user.company_id))

    if job_row is None:
        raise LookupError

    return build_template_configuration(
        job_row.status,
        job_row.reports_count,
        job_row.structure,
        str(job_row.id),
        job_row.error_message,
    )


async def confirm_template(
    user: CurrentUser,
    sections: list[TemplateSection],
) -> TemplateConfigurationActive:
    company_id = str(user.company_id)
    _, job_row = await template_repository.get_company_template_context(company_id)
    structure = build_structure(sections)
    template_id = str(uuid4())

    await template_repository.create_template(company_id, template_id, structure)
    await template_repository.set_active_template(company_id, template_id)

    if job_row is not None:
        await template_repository.update_template_analysis_job(
            str(job_row.id),
            "active",
            structure,
            template_id,
        )

    reports_count = job_row.reports_count if job_row is not None else 0

    return TemplateConfigurationActive(
        status="active",
        reports_count=reports_count,
        sections=sections,
    )
