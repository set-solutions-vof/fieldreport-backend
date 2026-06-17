from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src.models.enums.template_section_render_type import TemplateSectionRenderType


class TemplateSelectMetadataField(BaseModel):
    key: str
    label: str
    type: Literal["select"]
    options: list[str]
    required: bool = False


class TemplateScalarMetadataField(BaseModel):
    key: str
    label: str
    type: Literal["text", "date", "phone", "email", "boolean"]
    required: bool = False


TemplateMetadataField = Annotated[
    TemplateSelectMetadataField | TemplateScalarMetadataField,
    Field(discriminator="type"),
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
    metadata_fields: list[TemplateMetadataField] = Field(default_factory=list)
    sections: list[TemplateSection]
