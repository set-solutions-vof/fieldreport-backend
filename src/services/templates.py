from uuid import uuid4

from fastapi import UploadFile

from src.db import template_queries
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    StoredTemplateStructure,
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateSection,
)
from src.models.templates.records import TemplateAnalysisJobRecord
from src.models.templates.state import TemplateCompanyState
from src.services import templates_state
from src.storage import template_file_storage


async def load_template_company_state(company_id: str) -> TemplateCompanyState:
    company, job = await template_queries.fetch_company_template_context(company_id)

    return templates_state.resolve_template_company_state(company, job)


async def get_template_analysis_job(
    user: CurrentUser,
    job_id: str,
) -> TemplateAnalysisJobRecord:
    job_row = await template_queries.get_template_analysis_job(job_id, str(user.company_id))

    if job_row is None:
        raise LookupError

    return job_row


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

    await template_queries.replace_template_analysis_job(job_id, company_id, stored_files)

    return TemplateConfigurationExtracting(
        status="extracting",
        jobId=job_id,
        reports_count=len(files),
    )


async def confirm_template(
    user: CurrentUser,
    sections: list[TemplateSection],
) -> TemplateConfigurationActive:
    company_id = str(user.company_id)
    state = await load_template_company_state(company_id)
    structure = StoredTemplateStructure(sections=sections)
    template_id = str(uuid4())

    await template_queries.create_template(company_id, template_id, structure)
    await template_queries.set_active_template(company_id, template_id)

    if state.job_id is not None:
        await template_queries.update_template_analysis_job(
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


async def update_pending_template_structure(
    user: CurrentUser,
    job_id: str,
    sections: list[TemplateSection],
) -> None:
    structure = StoredTemplateStructure(sections=sections)
    await template_queries.update_pending_template_structure(
        job_id,
        str(user.company_id),
        structure,
    )
