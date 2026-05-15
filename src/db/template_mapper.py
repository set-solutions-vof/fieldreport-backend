import asyncpg

from src.models.templates.configuration import (
    StoredTemplateStructure,
    parse_stored_template_structure,
)
from src.models.templates.pipeline import TemplateAnalysisFile, TemplateAnalysisJob
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord


def map_company_template(row: asyncpg.Record) -> CompanyTemplateRecord:
    row_data = dict(row)
    structure = parse_stored_template_structure(row_data.get("structure"))
    if structure is not None:
        row_data["structure"] = structure
    else:
        row_data.pop("structure")

    return CompanyTemplateRecord.model_validate(row_data)


def map_template_analysis_job(row: asyncpg.Record) -> TemplateAnalysisJobRecord:
    row_data = dict(row)
    structure = parse_stored_template_structure(row_data.get("structure"))
    if structure is not None:
        row_data["structure"] = structure
    else:
        row_data.pop("structure")

    if row_data["error_message"] is None:
        row_data.pop("error_message")

    return TemplateAnalysisJobRecord.model_validate(row_data)


def map_claimed_template_analysis_job(row: asyncpg.Record) -> TemplateAnalysisJob:
    job = map_template_analysis_job(row)

    return TemplateAnalysisJob(
        id=str(job.id),
        company_id=str(job.company_id),
        status=job.status,
        reports_count=job.reports_count,
        template_id=str(job.template_id) if job.template_id is not None else None,
        error_message=job.error_message,
    )


def map_template_analysis_file(row: asyncpg.Record) -> TemplateAnalysisFile:
    return TemplateAnalysisFile.model_validate(dict(row))
