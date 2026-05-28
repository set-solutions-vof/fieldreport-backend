from uuid import uuid4

from fastapi import UploadFile

from src.db import template_queries
from src.models.auth.authentication import CurrentUser
from src.models.templates import status_resolver
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
    TemplateStatusProcessing,
)
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import TemplateAnalysisJobRecord
from src.storage import template_file_storage


async def load_template_configuration(company_id: str) -> TemplateStatus:
    active_template, job = await template_queries.fetch_template_configuration_context(company_id)

    return status_resolver.resolve_template_company_state(active_template, job)


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
) -> TemplateStatusProcessing:
    company_id = str(user.company_id)
    job_id = str(uuid4())
    stored_files = await template_file_storage.store_template_analysis_files(
        company_id,
        job_id,
        files,
    )

    await template_queries.replace_template_analysis_job(job_id, company_id, stored_files)

    return TemplateStatusProcessing(
        status="processing",
        job_id=job_id,
        source_reports_count=len(files),
    )


async def confirm_template(
    user: CurrentUser,
    sections: list[TemplateSection],
) -> TemplateStatusActive:
    company_id = str(user.company_id)
    job = await template_queries.fetch_latest_template_analysis_job(company_id)
    structure = TemplateStructure(sections=sections)
    template_id = str(uuid4())

    await template_queries.create_template(company_id, template_id, structure)
    await template_queries.set_active_template(company_id, template_id)
    await template_queries.delete_template_analysis_job(str(job.id), company_id)

    return TemplateStatusActive(
        status="active",
        source_reports_count=job.source_reports_count,
        sections=sections,
    )
