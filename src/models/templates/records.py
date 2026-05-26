from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.templates.domain import TemplateAnalysisJobStatus, TemplateStructure


class CompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    template_id: UUID | None = None
    structure: TemplateStructure = Field(default_factory=lambda: TemplateStructure(sections=[]))


class ActiveCompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    template_id: UUID
    structure: TemplateStructure


class TemplateAnalysisJobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    company_id: UUID
    template_id: UUID | None
    status: TemplateAnalysisJobStatus
    reports_count: int
    structure: TemplateStructure = Field(default_factory=lambda: TemplateStructure(sections=[]))
    error_message: str = "Template analysis failed"
    created_at: datetime
