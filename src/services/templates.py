from uuid import uuid4

from fastapi import UploadFile

from src.db import template_repository
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    StoredTemplateStructure,
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationFailed,
    TemplateConfigurationNotConfigured,
    TemplateConfigurationPendingReview,
    TemplateSection,
)
from src.models.templates.state import resolve_template_job_state
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
    state = await template_repository.get_template_company_state(str(user.company_id))

    return build_template_configuration(state)


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

    return build_template_configuration(resolve_template_job_state(job_row))


async def confirm_template(
    user: CurrentUser,
    sections: list[TemplateSection],
) -> TemplateConfigurationActive:
    company_id = str(user.company_id)
    state = await template_repository.get_template_company_state(company_id)
    structure = StoredTemplateStructure(sections=sections)
    template_id = str(uuid4())

    await template_repository.create_template(company_id, template_id, structure)
    await template_repository.set_active_template(company_id, template_id)

    if state.job_id is not None:
        await template_repository.update_template_analysis_job(
            str(state.job_id),
            "active",
            structure,
            template_id,
        )

    reports_count = state.reports_count if state.job_id is not None else 0

    return TemplateConfigurationActive(
        status="active",
        reports_count=reports_count,
        sections=sections,
    )
