from pydantic import BaseModel

from src.models.templates.domain import TemplateSection


class TemplateStructureRequest(BaseModel):
    sections: list[TemplateSection]
