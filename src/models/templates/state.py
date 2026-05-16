from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.templates.configuration import StoredTemplateStructure

TemplateViewStatus = Literal[
    "not_configured",
    "extracting",
    "pending_review",
    "active",
    "failed",
]


class TemplateCompanyState(BaseModel):
    model_config = ConfigDict(frozen=True)

    view_status: TemplateViewStatus
    structure: StoredTemplateStructure = StoredTemplateStructure(sections=[])
    job_id: UUID | None = None
    template_id: UUID | None = None
    reports_count: int = 0
    error_message: str = "Template analysis failed"
