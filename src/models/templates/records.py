from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.templates.domain import TemplateStructure


class ActiveCompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_template_id: UUID
    structure: TemplateStructure
    created_at: datetime
    version: int
    source_reports_count: int


class CompanyTemplateRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    structure: TemplateStructure
