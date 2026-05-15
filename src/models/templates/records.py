from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.templates.configuration import StoredTemplateStructure
from src.models.templates.pipeline import TemplateAnalysisJobStatus


class CompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    template_id: UUID | None
    structure: StoredTemplateStructure | None = None


class TemplateAnalysisJobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    company_id: UUID
    template_id: UUID | None
    status: TemplateAnalysisJobStatus
    reports_count: int
    structure: StoredTemplateStructure | None = None
    error_message: str | None
    created_at: datetime | None = None
