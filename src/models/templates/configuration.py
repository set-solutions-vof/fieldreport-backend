from typing import Literal

from pydantic import BaseModel

TemplateSectionRenderType = Literal[
    "text_block",
    "key_value_table",
    "measurement_table",
    "photo_grid",
]


class TemplateSection(BaseModel):
    id: str
    label: str
    render_type: TemplateSectionRenderType
    fields: list[str] | None = None


class TemplateConfigurationNotConfigured(BaseModel):
    status: Literal["not_configured"]


class TemplateConfigurationExtracting(BaseModel):
    status: Literal["extracting"]
    jobId: str
    reports_count: int


class TemplateConfigurationPendingReview(BaseModel):
    status: Literal["pending_review"]
    reports_count: int
    sections: list[TemplateSection]


class TemplateConfigurationActive(BaseModel):
    status: Literal["active"]
    reports_count: int
    sections: list[TemplateSection]


class TemplateConfigurationFailed(BaseModel):
    status: Literal["failed"]
    reports_count: int
    error_message: str


class StoredTemplateStructure(BaseModel):
    sections: list[TemplateSection]


def parse_stored_template_structure(value: object) -> StoredTemplateStructure | None:
    if value is None:
        return None

    if isinstance(value, StoredTemplateStructure):
        return value

    if isinstance(value, str):
        return StoredTemplateStructure.model_validate_json(value)

    if isinstance(value, dict):
        return StoredTemplateStructure.model_validate(value)

    raise TypeError(f"Unsupported structure value: {type(value)!r}")


TemplateConfiguration = (
    TemplateConfigurationNotConfigured
    | TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
)

TemplateAnalysisConfiguration = (
    TemplateConfigurationExtracting
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
)
