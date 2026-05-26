from typing import Literal

from pydantic import BaseModel

TemplateSectionRenderType = Literal[
    "text_block",
    "key_value_table",
    "measurement_table",
    "photo_grid",
]

TemplateAnalysisJobStatus = Literal[
    "queued",
    "processing",
    "pending_review",
    "active",
    "failed",
]


class TemplateSectionGroup(BaseModel):
    id: str
    label: str
    fields: list[str]


class TemplateSection(BaseModel):
    id: str
    label: str
    order: int = 0
    render_type: TemplateSectionRenderType
    fields: list[str] | None = None
    found_in: int = 0
    groups: list[TemplateSectionGroup] | None = None


class TemplateStructure(BaseModel):
    sections: list[TemplateSection]
