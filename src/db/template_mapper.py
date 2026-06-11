from collections.abc import Mapping

from src.models.templates.domain import TemplateStructure
from src.models.templates.pipeline import TemplateAnalysisFile
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


def map_optional_active_company_template(
    row: Mapping[str, object],
) -> ActiveCompanyTemplateRecord | None:
    if row["current_template_id"] is None:
        return None

    return map_active_company_template(row)


def parse_template_structure(value: object) -> TemplateStructure:
    return (
        TemplateStructure.model_validate_json(value)
        if isinstance(value, str)
        else TemplateStructure.model_validate(value)
    )


def map_active_company_template(row: Mapping[str, object]) -> ActiveCompanyTemplateRecord:
    row_data = dict(row)
    row_data["structure"] = parse_template_structure(row_data["structure"])

    return ActiveCompanyTemplateRecord.model_validate(row_data)


def map_template_analysis_job(row: Mapping[str, object]) -> TemplateAnalysisJobRecord:
    row_data = dict(row)
    if row_data.get("structure") is not None:
        row_data["structure"] = parse_template_structure(row_data["structure"])
    else:
        row_data["structure"] = TemplateStructure(sections=[])

    if row_data["failure_message"] is None:
        row_data.pop("failure_message")

    return TemplateAnalysisJobRecord.model_validate(row_data)


def map_template_analysis_file(row: Mapping[str, object]) -> TemplateAnalysisFile:
    return TemplateAnalysisFile.model_validate(dict(row))
