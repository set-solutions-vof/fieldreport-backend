from typing import Literal

from pydantic import BaseModel

TemplateSectionRenderType = Literal[
    "text_block",
    "key_value_table",
    "measurement_table",
    "photo_grid",
]


class TemplateSectionGroup(BaseModel):
    id: str
    label: str
    fields: list[str]


class TemplateSection(BaseModel):
    id: str
    label: str
    order: int = 0
    render_type: TemplateSectionRenderType
    fields: list[str] | None = None
    found_in: int = 0
    groups: list[TemplateSectionGroup] | None = None


class TemplateConfigurationNotConfigured(BaseModel):
    status: Literal["not_configured"]


class TemplateConfigurationExtracting(BaseModel):
    status: Literal["extracting"]
    jobId: str
    reports_count: int


class TemplateConfigurationPendingReview(BaseModel):
    status: Literal["pending_review"]
    job_id: str
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
