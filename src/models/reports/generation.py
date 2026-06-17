from pydantic import BaseModel

from src.models.enums.confidence_level import ConfidenceLevel


class GeneratedReportSection(BaseModel):
    id: str
    generated_content: str
    confidence_level: ConfidenceLevel
    confidence_score: float
    transcription_refs: list[int] = []
    image_refs: list[int] = []


class GeneratedReportSectionList(BaseModel):
    sections: list[GeneratedReportSection]
