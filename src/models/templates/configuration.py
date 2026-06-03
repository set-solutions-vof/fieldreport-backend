from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src.models.templates.domain import TemplateMetadataField, TemplateSection


class TemplateStatusNotConfigured(BaseModel):
    status: Literal["not_configured"]


class TemplateStatusProcessing(BaseModel):
    status: Literal["processing"]
    job_id: str
    source_reports_count: int


class TemplateStatusPendingReview(BaseModel):
    status: Literal["pending_review"]
    job_id: str
    source_reports_count: int
    metadata_fields: list[TemplateMetadataField] = Field(default_factory=list)
    sections: list[TemplateSection]


class TemplateStatusActive(BaseModel):
    status: Literal["active"]
    source_reports_count: int
    metadata_fields: list[TemplateMetadataField] = Field(default_factory=list)
    sections: list[TemplateSection]


class TemplateStatusFailed(BaseModel):
    status: Literal["failed"]
    source_reports_count: int
    failure_message: str


TemplateStatus = Annotated[
    TemplateStatusNotConfigured
    | TemplateStatusProcessing
    | TemplateStatusPendingReview
    | TemplateStatusActive
    | TemplateStatusFailed,
    Field(discriminator="status"),
]
