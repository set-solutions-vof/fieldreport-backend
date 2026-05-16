from pydantic import BaseModel

from src.models.templates.configuration import TemplateSection


class TemplateConfigurationRequest(BaseModel):
    sections: list[TemplateSection]


class UpdateTemplateStructureRequest(BaseModel):
    sections: list[TemplateSection]
