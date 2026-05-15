from uuid import uuid4

from src.models.templates.configuration import StoredTemplateStructure, TemplateSection
from src.models.templates.state import TemplateCompanyState
from src.services.template_configuration import build_template_configuration


def test_build_template_configuration_maps_pending_review_status() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", type="text_block")]
    )
    state = TemplateCompanyState(
        view_status="pending_review",
        structure=structure,
        reports_count=2,
    )

    result = build_template_configuration(state)

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "reports_count": 2,
        "sections": [{"id": "summary", "label": "Summary", "type": "text_block"}],
    }


def test_build_template_configuration_maps_failed_status() -> None:
    state = TemplateCompanyState(
        view_status="failed",
        reports_count=1,
        error_message="bad response",
    )

    result = build_template_configuration(state)

    assert result.model_dump() == {
        "status": "failed",
        "reports_count": 1,
        "error_message": "bad response",
    }


def test_build_template_configuration_maps_extracting_status() -> None:
    job_id = uuid4()
    state = TemplateCompanyState(
        view_status="extracting",
        job_id=job_id,
        reports_count=4,
    )

    result = build_template_configuration(state)

    assert result.model_dump() == {
        "status": "extracting",
        "jobId": str(job_id),
        "reports_count": 4,
    }
