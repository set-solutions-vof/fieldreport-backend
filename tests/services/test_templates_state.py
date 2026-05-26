from datetime import UTC, datetime
from uuid import uuid4

from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord
from src.services import templates_state


def build_company(
    template_id=None,
    structure: TemplateStructure = TemplateStructure(sections=[]),
):
    return CompanyTemplateRecord(template_id=template_id, structure=structure)


def build_job(
    *,
    status: str,
    structure: TemplateStructure = TemplateStructure(sections=[]),
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
        created_at=datetime.now(UTC),
    )


def test_resolve_template_company_state_returns_not_configured() -> None:
    result = templates_state.resolve_template_company_state(build_company(), None)

    assert result.status == "not_configured"


def test_resolve_template_company_state_returns_pending_review_job() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure, reports_count=3)

    result = templates_state.resolve_template_company_state(build_company(), job)

    assert result.status == "pending_review"
    assert result.sections == structure.sections
    assert result.job_id == str(job.id)
    assert result.reports_count == 3


def test_resolve_template_company_state_returns_unfinished_job_before_active_template() -> None:
    active_structure = TemplateStructure(
        sections=[TemplateSection(id="active", label="Active", render_type="text_block")]
    )
    pending_structure = TemplateStructure(
        sections=[TemplateSection(id="pending", label="Pending", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=pending_structure)

    result = templates_state.resolve_template_company_state(
        build_company(uuid4(), active_structure),
        job,
    )

    assert result.status == "pending_review"
    assert result.sections == pending_structure.sections


def test_resolve_template_company_state_maps_queued_job_to_processing() -> None:
    job = build_job(status="queued", reports_count=3)

    result = templates_state.resolve_template_company_state(build_company(), job)

    assert result.status == "processing"
    assert result.job_id == str(job.id)
    assert result.reports_count == 3


def test_resolve_template_company_state_returns_active_template_when_no_job() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    template_id = uuid4()

    result = templates_state.resolve_template_company_state(
        build_company(template_id, structure), None
    )

    assert result.status == "active"
    assert result.sections == structure.sections


def test_resolve_template_company_state_prefers_active_template_over_failed_job() -> None:
    template_id = uuid4()
    active_structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="failed", error_message="model error")

    result = templates_state.resolve_template_company_state(
        build_company(template_id, active_structure), job
    )

    assert result.status == "active"
    assert result.sections == active_structure.sections


def test_resolve_template_company_state_returns_active_from_active_job() -> None:
    template_id = uuid4()
    active_structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(
        status="active",
        structure=TemplateStructure(
            sections=[TemplateSection(id="draft", label="Draft", render_type="text_block")]
        ),
        template_id=template_id,
        reports_count=4,
    )

    result = templates_state.resolve_template_company_state(
        build_company(template_id, active_structure), job
    )

    assert result.status == "active"
    assert result.sections == active_structure.sections
    assert result.reports_count == 4


def test_resolve_template_company_state_returns_failed_without_active_template() -> None:
    job = build_job(status="failed", error_message="model error", reports_count=2)

    result = templates_state.resolve_template_company_state(build_company(), job)

    assert result.status == "failed"
    assert result.error_message == "model error"


def test_resolve_template_job_state_returns_processing() -> None:
    job = build_job(status="processing", reports_count=2)

    result = templates_state.resolve_template_job_state(job)

    assert result.status == "processing"


def test_resolve_template_job_state_returns_pending_review() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure)

    result = templates_state.resolve_template_job_state(job)

    assert result.status == "pending_review"
    assert result.sections == structure.sections


def test_resolve_template_job_state_returns_failed() -> None:
    job = build_job(status="failed", error_message="model error", reports_count=2)

    result = templates_state.resolve_template_job_state(job)

    assert result.status == "failed"
    assert result.error_message == "model error"
    assert result.reports_count == 2


def test_resolve_template_job_state_returns_active_from_job_structure() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    template_id = uuid4()
    job = build_job(status="active", structure=structure, template_id=template_id, reports_count=5)

    result = templates_state.resolve_template_job_state(job)

    assert result.status == "active"
    assert result.sections == structure.sections
