from uuid import uuid4

from src.http.v1.response.template import template_configuration_response
from src.models.templates.configuration import StoredTemplateStructure, TemplateSection
from src.models.templates.records import TemplateAnalysisJobRecord
from src.models.templates.state import TemplateCompanyState
from src.services import templates_state


def build_job(
    *,
    status: str,
    structure: StoredTemplateStructure = StoredTemplateStructure(sections=[]),
    error_message: str = "Template analysis failed",
    reports_count: int = 1,
    template_id=None,
) -> TemplateAnalysisJobRecord:
    return TemplateAnalysisJobRecord(
        id=uuid4(),
        company_id=uuid4(),
        template_id=template_id,
        status=status,
        reports_count=reports_count,
        structure=structure,
        error_message=error_message,
        created_at=None,
    )


def test_template_configuration_response_maps_not_configured_status() -> None:
    result = template_configuration_response(TemplateCompanyState(view_status="not_configured"))

    assert result.model_dump() == {"status": "not_configured"}


def test_template_configuration_response_maps_pending_review_status() -> None:
    job_id = uuid4()
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    state = TemplateCompanyState(
        view_status="pending_review",
        job_id=job_id,
        structure=structure,
        reports_count=2,
    )

    result = template_configuration_response(state)

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "job_id": str(job_id),
        "reports_count": 2,
        "sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}],
    }


def test_template_configuration_response_maps_failed_status() -> None:
    state = TemplateCompanyState(
        view_status="failed",
        reports_count=1,
        error_message="bad response",
    )

    result = template_configuration_response(state)

    assert result.model_dump() == {
        "status": "failed",
        "reports_count": 1,
        "error_message": "bad response",
    }


def test_template_configuration_response_maps_extracting_status() -> None:
    job_id = uuid4()
    state = TemplateCompanyState(
        view_status="extracting",
        job_id=job_id,
        reports_count=4,
    )

    result = template_configuration_response(state)

    assert result.model_dump() == {
        "status": "extracting",
        "jobId": str(job_id),
        "reports_count": 4,
    }


def test_template_configuration_response_maps_active_status() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    state = TemplateCompanyState(view_status="active", structure=structure)

    result = template_configuration_response(state)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 0,
        "sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}],
    }


def test_template_configuration_response_maps_active_job() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="active", structure=structure, template_id=uuid4(), reports_count=5)

    result = template_configuration_response(templates_state.resolve_template_job_state(job))

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 5,
        "sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}],
    }


def test_template_configuration_response_maps_extracting_job() -> None:
    job = build_job(status="queued", reports_count=3)

    result = template_configuration_response(templates_state.resolve_template_job_state(job))

    assert result.model_dump() == {
        "status": "extracting",
        "jobId": str(job.id),
        "reports_count": 3,
    }


def test_template_configuration_response_maps_pending_review_job() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure, reports_count=2)

    result = template_configuration_response(templates_state.resolve_template_job_state(job))

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "job_id": str(job.id),
        "reports_count": 2,
        "sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}],
    }


def test_template_configuration_response_maps_failed_job() -> None:
    job = build_job(status="failed", error_message="model error", reports_count=1)

    result = template_configuration_response(templates_state.resolve_template_job_state(job))

    assert result.model_dump() == {
        "status": "failed",
        "reports_count": 1,
        "error_message": "model error",
    }
