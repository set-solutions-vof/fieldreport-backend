from src.db.template_mapper import build_section_key, build_structure, map_sections
from src.models.templates.template import TemplateSection


def test_build_section_key_normalizes_label() -> None:
    assert build_section_key("Project Gegevens!") == "project_gegevens"


def test_build_structure_serializes_sections_in_order() -> None:
    sections = [
        TemplateSection(id="summary", label="Summary", type="text_block"),
        TemplateSection(id="photos", label="Photos", type="photo_grid"),
    ]

    result = build_structure(sections)

    assert result == {
        "sections": [
            {
                "id": "summary",
                "key": "summary",
                "label": "Summary",
                "order": 0,
                "render_type": "text_block",
                "fields": None,
            },
            {
                "id": "photos",
                "key": "photos",
                "label": "Photos",
                "order": 1,
                "render_type": "photo_grid",
                "fields": None,
            },
        ]
    }


def test_map_sections_returns_empty_list_for_missing_structure() -> None:
    assert map_sections(None) == []


def test_map_sections_restores_ordered_sections() -> None:
    structure = {
        "sections": [
            {
                "id": "photos",
                "key": "photos",
                "label": "Photos",
                "order": 1,
                "render_type": "photo_grid",
                "fields": None,
            },
            {
                "id": "summary",
                "key": "summary",
                "label": "Summary",
                "order": 0,
                "render_type": "text_block",
                "fields": None,
            },
        ]
    }

    result = map_sections(structure)

    assert [section.id for section in result] == ["summary", "photos"]
