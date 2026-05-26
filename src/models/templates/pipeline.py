from pydantic import BaseModel

from src.models.templates.domain import TemplateSection


class TemplateAnalysisFile(BaseModel):
    file_name: str
    storage_path: str


class TemplateAnalysisDocument(BaseModel):
    file_name: str
    extracted_text: str
    visual_summary: str


class TemplateAnalysisDocumentList(BaseModel):
    documents: list[TemplateAnalysisDocument]


class TemplateVisualAnalysis(BaseModel):
    document_type: str
    visual_summary: str
    likely_sections: list[str]
    table_patterns: list[str]
    photo_expectations: list[str]


class TemplateSectionList(BaseModel):
    sections: list[TemplateSection]
