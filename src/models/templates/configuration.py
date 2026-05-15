from typing import Literal

from pydantic import BaseModel

TemplateSectionType = Literal[
    "text_block",
    "key_value_table",
    "measurement_table",
    "photo_grid",
]


class TemplateSection(BaseModel):
    id: str
    label: str
    type: TemplateSectionType
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
