from typing import Literal

from pydantic import BaseModel

TemplateSectionType = Literal["text", "kv", "measure", "photo"]
TemplateStatus = Literal["not_configured", "extracting", "pending_review", "active"]


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
