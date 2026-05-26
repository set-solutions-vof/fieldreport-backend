from uuid import uuid4

from src.models.templates.configuration import StoredTemplateStructure, TemplateSection
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord
from src.services import templates_state


def build_company(
    template_id=None,
    structure: StoredTemplateStructure = StoredTemplateStructure(sections=[]),
) -> CompanyTemplateRecord:
    return CompanyTemplateRecord(
        template_id=template_id,
        structure=structure,
    )


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


def test_resolve_template_company_state_returns_not_configured() -> None:
    state = templates_state.resolve_template_company_state(build_company(), None)

    assert state.view_status == "not_configured"


def test_resolve_template_company_state_returns_pending_review_job() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure, reports_count=3)

    state = templates_state.resolve_template_company_state(build_company(), job)

    assert state.view_status == "pending_review"
    assert state.structure == structure
    assert state.job_id == job.id
    assert state.reports_count == 3


def test_resolve_template_company_state_maps_queued_job_to_extracting() -> None:
    job = build_job(status="queued", reports_count=3)

    state = templates_state.resolve_template_company_state(build_company(), job)

    assert state.view_status == "extracting"
    assert state.job_id == job.id
    assert state.reports_count == 3


def test_resolve_template_company_state_returns_active_template_when_no_job() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    template_id = uuid4()

    state = templates_state.resolve_template_company_state(
        build_company(template_id, structure), None
    )

    assert state.view_status == "active"
    assert state.structure == structure
    assert state.template_id == template_id


def test_resolve_template_company_state_prefers_active_template_over_failed_job() -> None:
    template_id = uuid4()
    active_structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="failed", error_message="model error")

    state = templates_state.resolve_template_company_state(
        build_company(template_id, active_structure), job
    )

    assert state.view_status == "active"
    assert state.structure == active_structure


def test_resolve_template_company_state_returns_active_from_active_job() -> None:
    template_id = uuid4()
    active_structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(
        status="active",
        structure=StoredTemplateStructure(
            sections=[TemplateSection(id="draft", label="Draft", render_type="text_block")]
        ),
        template_id=template_id,
        reports_count=4,
    )

    state = templates_state.resolve_template_company_state(
        build_company(template_id, active_structure), job
    )

    assert state.view_status == "active"
    assert state.structure == active_structure
    assert state.template_id == template_id
    assert state.reports_count == 4


def test_resolve_template_company_state_returns_failed_without_active_template() -> None:
    job = build_job(status="failed", error_message="model error", reports_count=2)

    state = templates_state.resolve_template_company_state(build_company(), job)

    assert state.view_status == "failed"
    assert state.error_message == "model error"


def test_resolve_template_job_state_returns_extracting() -> None:
    job = build_job(status="processing", reports_count=2)

    state = templates_state.resolve_template_job_state(job)

    assert state.view_status == "extracting"


def test_resolve_template_job_state_returns_pending_review() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure)

    state = templates_state.resolve_template_job_state(job)

    assert state.view_status == "pending_review"
    assert state.structure == structure


def test_resolve_template_job_state_returns_failed() -> None:
    job = build_job(status="failed", error_message="model error", reports_count=2)

    state = templates_state.resolve_template_job_state(job)

    assert state.view_status == "failed"
    assert state.error_message == "model error"
    assert state.reports_count == 2


def test_resolve_template_job_state_returns_active_from_job_structure() -> None:
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    template_id = uuid4()
    job = build_job(status="active", structure=structure, template_id=template_id, reports_count=5)

    state = templates_state.resolve_template_job_state(job)

    assert state.view_status == "active"
    assert state.structure == structure
    assert state.template_id == template_id
