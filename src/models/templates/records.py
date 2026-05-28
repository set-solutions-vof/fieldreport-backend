from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.templates.domain import TemplateAnalysisJobStatus, TemplateStructure


class ActiveCompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_template_id: UUID
    structure: TemplateStructure


class TemplateAnalysisJobRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    company_id: UUID
    status: TemplateAnalysisJobStatus
    source_reports_count: int
    structure: TemplateStructure
    failure_message: str = "Template analysis failed"
    created_at: datetime
