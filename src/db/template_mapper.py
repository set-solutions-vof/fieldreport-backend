import asyncpg

from src.models.templates.configuration import StoredTemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile, TemplateAnalysisJob
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord


def parse_structure_column(value: object) -> StoredTemplateStructure | None:
    if value is None:
        return None

    if isinstance(value, StoredTemplateStructure):
        return value

    if isinstance(value, str):
        return StoredTemplateStructure.model_validate_json(value)

    if isinstance(value, dict):
        return StoredTemplateStructure.model_validate(value)

    raise TypeError(f"Unsupported structure value: {type(value)!r}")


def map_company_template(row: asyncpg.Record) -> CompanyTemplateRecord:
    row_data = dict(row)
    row_data["structure"] = parse_structure_column(row_data.get("structure"))

    return CompanyTemplateRecord.model_validate(row_data)


def map_template_analysis_job(row: asyncpg.Record) -> TemplateAnalysisJobRecord:
    row_data = dict(row)
    row_data["structure"] = parse_structure_column(row_data.get("structure"))

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
