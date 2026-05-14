from src.db.template_mapper import build_structure
from src.models.templates.template import TemplateSection
from src.services.template_configuration import build_template_configuration


def test_build_template_configuration_maps_pending_review_status() -> None:
    structure = build_structure([TemplateSection(id="summary", label="Summary", type="text_block")])

    result = build_template_configuration("pending_review", 2, structure)

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "reports_count": 2,
        "sections": [{"id": "summary", "label": "Summary", "type": "text_block"}],
    }


def test_build_template_configuration_maps_failed_status() -> None:
    result = build_template_configuration("failed", 1, None, error_message="bad response")

    assert result.model_dump() == {
        "status": "failed",
        "reports_count": 1,
        "error_message": "bad response",
    }
