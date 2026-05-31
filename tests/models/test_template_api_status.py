from typing import get_args

from src.models.enums.template_api_status import TemplateApiStatus


def test_template_api_status_contains_public_status_values() -> None:
    assert get_args(TemplateApiStatus) == (
        "not_configured",
        "processing",
        "pending_review",
        "active",
        "failed",
    )
