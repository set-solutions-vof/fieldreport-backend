import re

from src.models.templates.template import (
    StoredTemplateSection,
    StoredTemplateStructure,
    TemplateSection,
)


def build_structure(sections: list[TemplateSection]) -> StoredTemplateStructure:
    return {"sections": [build_stored_section(s, i) for i, s in enumerate(sections)]}


def build_stored_section(section: TemplateSection, order: int) -> StoredTemplateSection:
    return {
        "id": section.id,
        "key": build_section_key(section.label),
        "label": section.label,
        "order": order,
        "render_type": section.type,
        "fields": section.fields,
    }


def build_section_key(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def map_sections(structure: StoredTemplateStructure | None) -> list[TemplateSection]:
    if structure is None:
        return []

    return [map_section(s) for s in sorted(structure["sections"], key=lambda s: s["order"])]


def map_section(section: StoredTemplateSection) -> TemplateSection:
    return TemplateSection(
        id=section["id"],
        label=section["label"],
        type=section["render_type"],
        fields=section.get("fields"),
    )
