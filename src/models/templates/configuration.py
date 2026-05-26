from typing import Literal

from pydantic import BaseModel, Field

from src.models.templates.domain import TemplateSection


class TemplateConfigurationNotConfigured(BaseModel):
    status: Literal["not_configured"]


class TemplateConfigurationProcessing(BaseModel):
    status: Literal["processing"]
    job_id: str = Field(serialization_alias="jobId")
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


TemplateConfiguration = (
    TemplateConfigurationNotConfigured
    | TemplateConfigurationProcessing
    | TemplateConfigurationPendingReview
    | TemplateConfigurationActive
    | TemplateConfigurationFailed
)
