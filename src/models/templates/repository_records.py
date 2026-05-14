from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.models.templates.template import StoredTemplateStructure
from src.models.templates.template_analysis import TemplateAnalysisJobStatus


@dataclass(frozen=True)
class CompanyTemplateRecord:
    active_template_id: UUID | None
    active_structure: StoredTemplateStructure | None


@dataclass(frozen=True)
class TemplateAnalysisJobRecord:
    id: UUID
    company_id: UUID
    template_id: UUID | None
    status: TemplateAnalysisJobStatus
    reports_count: int
    structure: StoredTemplateStructure | None
    error_message: str | None
    created_at: datetime
