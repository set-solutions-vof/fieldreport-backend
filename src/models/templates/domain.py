from pydantic import BaseModel

from src.models.enums.template_section_render_type import TemplateSectionRenderType


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
