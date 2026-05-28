from datetime import UTC, datetime
from uuid import uuid4

from src.models.templates import status_resolver
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord, TemplateAnalysisJobRecord


def build_active_template(
    structure: TemplateStructure = TemplateStructure(sections=[]),
) -> ActiveCompanyTemplateRecord:
    return ActiveCompanyTemplateRecord(current_template_id=uuid4(), structure=structure)


def build_job(
    *,
    status: str,
    structure: TemplateStructure = TemplateStructure(sections=[]),
    failure_message: str = "Template analysis failed",
    source_reports_count: int = 1,
) -> TemplateAnalysisJobRecord:
    return TemplateAnalysisJobRecord(
        id=uuid4(),
        company_id=uuid4(),
        status=status,
        source_reports_count=source_reports_count,
        structure=structure,
        failure_message=failure_message,
        created_at=datetime.now(UTC),
    )


def test_resolve_template_company_state_returns_not_configured() -> None:
    result = status_resolver.resolve_template_company_state(None, None)

    assert result.status == "not_configured"


def test_resolve_template_company_state_returns_pending_review_job() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure, source_reports_count=3)

    result = status_resolver.resolve_template_company_state(None, job)

    assert result.status == "pending_review"
    assert result.sections == structure.sections
    assert result.job_id == str(job.id)
    assert result.source_reports_count == 3


def test_resolve_template_company_state_returns_unfinished_job_before_active_template() -> None:
    active_structure = TemplateStructure(
        sections=[TemplateSection(id="active", label="Active", render_type="text_block")]
    )
    pending_structure = TemplateStructure(
        sections=[TemplateSection(id="pending", label="Pending", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=pending_structure)

    result = status_resolver.resolve_template_company_state(
        build_active_template(active_structure),
        job,
    )

    assert result.status == "pending_review"
    assert result.sections == pending_structure.sections


def test_resolve_template_company_state_maps_queued_job_to_processing() -> None:
    job = build_job(status="queued", source_reports_count=3)

    result = status_resolver.resolve_template_company_state(None, job)

    assert result.status == "processing"
    assert result.job_id == str(job.id)
    assert result.source_reports_count == 3


def test_resolve_template_company_state_returns_active_template_when_no_job() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    result = status_resolver.resolve_template_company_state(build_active_template(structure), None)

    assert result.status == "active"
    assert result.sections == structure.sections


def test_resolve_template_company_state_returns_failed_job_before_active_template() -> None:
    active_structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="failed", failure_message="model error", source_reports_count=2)

    result = status_resolver.resolve_template_company_state(
        build_active_template(active_structure), job
    )

    assert result.status == "failed"
    assert result.failure_message == "model error"
    assert result.source_reports_count == 2


def test_resolve_template_company_state_returns_failed_without_active_template() -> None:
    job = build_job(status="failed", failure_message="model error", source_reports_count=2)

    result = status_resolver.resolve_template_company_state(None, job)

    assert result.status == "failed"
    assert result.failure_message == "model error"


def test_resolve_template_job_state_returns_processing() -> None:
    job = build_job(status="processing", source_reports_count=2)

    result = status_resolver.resolve_template_job_state(job)

    assert result.status == "processing"


def test_resolve_template_job_state_returns_pending_review() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="pending_review", structure=structure)

    result = status_resolver.resolve_template_job_state(job)

    assert result.status == "pending_review"
    assert result.sections == structure.sections


def test_resolve_template_job_state_returns_failed() -> None:
    job = build_job(status="failed", failure_message="model error", source_reports_count=2)

    result = status_resolver.resolve_template_job_state(job)

    assert result.status == "failed"
    assert result.failure_message == "model error"
    assert result.source_reports_count == 2


def test_resolve_template_job_state_returns_active_from_job_structure() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    job = build_job(status="active", structure=structure, source_reports_count=5)

    result = status_resolver.resolve_template_job_state(job)

    assert result.status == "active"
    assert result.sections == structure.sections
