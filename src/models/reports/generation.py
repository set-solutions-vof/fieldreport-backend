from pydantic import BaseModel

from src.models.enums.confidence_level import ConfidenceLevel


class GeneratedReportSection(BaseModel):
    id: str
    generated_content: str
    confidence_level: ConfidenceLevel
    confidence_score: float


class GeneratedReportSectionList(BaseModel):
    sections: list[GeneratedReportSection]
