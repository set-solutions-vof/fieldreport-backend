import asyncpg

from src.models.templates.domain import TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


def parse_template_structure(value: str) -> TemplateStructure:
    return TemplateStructure.model_validate_json(value)


def map_optional_active_company_template(
    row: asyncpg.Record,
) -> ActiveCompanyTemplateRecord | None:
    if row["current_template_id"] is None:
        return None

    return map_active_company_template(row)


def map_active_company_template(row: asyncpg.Record) -> ActiveCompanyTemplateRecord:
    row_data = dict(row)
    row_data["structure"] = parse_template_structure(row_data["structure"])

    return ActiveCompanyTemplateRecord.model_validate(row_data)


def map_template_analysis_job(row: asyncpg.Record) -> TemplateAnalysisJobRecord:
    row_data = dict(row)
    if row_data.get("structure") is not None:
        row_data["structure"] = parse_template_structure(row_data["structure"])
    else:
        row_data["structure"] = TemplateStructure(sections=[])

    if row_data["failure_message"] is None:
        row_data.pop("failure_message")

    return TemplateAnalysisJobRecord.model_validate(row_data)


def map_template_analysis_file(row: asyncpg.Record) -> TemplateAnalysisFile:
    return TemplateAnalysisFile.model_validate(dict(row))
