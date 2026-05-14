from typing import Literal

from pydantic import BaseModel

from src.models.templates.template import TemplateSection

TemplateAnalysisJobStatus = Literal[
    "queued",
    "processing",
    "extracting",
    "pending_review",
    "active",
    "failed",
]


class TemplateAnalysisFile(BaseModel):
    file_name: str
    storage_path: str


class TemplateAnalysisJob(BaseModel):
    id: str
    company_id: str
    status: TemplateAnalysisJobStatus
    reports_count: int
    structure: list[TemplateSection] | None = None
    template_id: str | None = None
    error_message: str | None = None


class TemplateAnalysisDocument(BaseModel):
    file_name: str
    extracted_text: str
    visual_summary: str


class TemplateVisualAnalysis(BaseModel):
    document_type: str
    visual_summary: str
    likely_sections: list[str]
    table_patterns: list[str]
    photo_expectations: list[str]


class TemplateSectionList(BaseModel):
    sections: list[TemplateSection]
