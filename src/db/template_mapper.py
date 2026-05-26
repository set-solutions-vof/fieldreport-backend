import asyncpg

from src.models.templates.domain import TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    CompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


def parse_template_structure(value: str) -> TemplateStructure:
    return TemplateStructure.model_validate_json(value)


def map_company_template(row: asyncpg.Record) -> CompanyTemplateRecord:
    row_data = dict(row)
    if row_data.get("structure") is not None:
        row_data["structure"] = parse_template_structure(row_data["structure"])
    else:
        row_data.pop("structure")

    return CompanyTemplateRecord.model_validate(row_data)


def map_active_company_template(row: asyncpg.Record) -> ActiveCompanyTemplateRecord:
    row_data = dict(row)
    row_data["structure"] = parse_template_structure(row_data["structure"])

    return ActiveCompanyTemplateRecord.model_validate(row_data)


def map_template_analysis_job(row: asyncpg.Record) -> TemplateAnalysisJobRecord:
    row_data = dict(row)
    if row_data.get("structure") is None:
        row_data.pop("structure")
    else:
        row_data["structure"] = parse_template_structure(row_data["structure"])

    if row_data["error_message"] is None:
        row_data.pop("error_message")

    return TemplateAnalysisJobRecord.model_validate(row_data)


def map_template_analysis_file(row: asyncpg.Record) -> TemplateAnalysisFile:
    return TemplateAnalysisFile.model_validate(dict(row))
