from pydantic import BaseModel

from src.models.templates.template import TemplateSection


class TemplateConfigurationRequest(BaseModel):
    sections: list[TemplateSection]
