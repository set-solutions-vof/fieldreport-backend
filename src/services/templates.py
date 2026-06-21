from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.db.template import queries
from src.exceptions import TemplateAnalysisJobNotFound, TemplateConfirmationNotAllowed
from src.models.auth.authentication import CurrentUser
from src.models.templates import status_resolver
from src.models.templates.configuration import (
    TemplateStatus,
    TemplateStatusActive,
    TemplateStatusProcessing,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import TemplateAnalysisJobRecord
from src.storage import blob


async def load_template_configuration(company_id: str) -> TemplateStatus:
    active_template, job = await queries.fetch_template_configuration_context(company_id)

    return status_resolver.resolve_template_company_state(active_template, job)


async def get_template_analysis_job(
    user: CurrentUser,
    job_id: str,
) -> TemplateAnalysisJobRecord:
    company_id = str(user.company_id)
    job_row = await queries.get_template_analysis_job(job_id, company_id)

    if job_row is None:
        raise TemplateAnalysisJobNotFound(job_id, company_id)

    return job_row


async def start_template_analysis(
    user: CurrentUser,
    files: list[UploadFile],
) -> TemplateStatusProcessing:
    company_id = str(user.company_id)
    job_id = str(uuid4())

    stored_files: list[TemplateAnalysisFile] = []
    for file in files:
        original_file_name = file.filename or f"{uuid4()}.pdf"
        key = f"{company_id}/{job_id}/{uuid4()}{Path(original_file_name).suffix}"
        data = await file.read()
        await blob.upload_file(
            "templates",
            key,
            data,
            file.content_type or "application/octet-stream",
        )
        stored_files.append(
            TemplateAnalysisFile(original_file_name=original_file_name, stored_file_path=key)
        )

    await queries.replace_template_analysis_job(job_id, company_id, stored_files)

    return TemplateStatusProcessing(
        status="processing",
        job_id=job_id,
        source_reports_count=len(files),
    )


async def confirm_template(
    user: CurrentUser,
    structure: TemplateStructure,
) -> TemplateStatusActive:
    company_id = str(user.company_id)
    pending_job = await queries.fetch_pending_review_job(company_id)
    active_template = await queries.fetch_optional_active_company_template(company_id)

    source = pending_job or active_template
    if source is None:
        raise TemplateConfirmationNotAllowed()

    template_id = str(uuid4())
    await queries.create_template(company_id, template_id, structure, source.source_reports_count)
    await queries.set_active_template(company_id, template_id)

    if pending_job is not None:
        await queries.archive_template_analysis_job(str(pending_job.id), company_id)

    active_template = await queries.fetch_active_company_template(company_id)

    return status_resolver.build_template_status_active(active_template)
