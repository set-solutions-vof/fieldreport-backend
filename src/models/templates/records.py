from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.enums.template_analysis_job_status import TemplateAnalysisJobStatus
from src.models.templates.domain import TemplateStructure


class ActiveCompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_template_id: UUID
    structure: TemplateStructure


class CompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
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
