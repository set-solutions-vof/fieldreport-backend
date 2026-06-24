from datetime import UTC, datetime
from uuid import uuid4

from src.models.templates import status_resolver
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord

FIXED_TEMPLATE_CREATED_AT = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)


def build_active_template(
    structure: TemplateStructure = TemplateStructure(sections=[]),
    version: int = 1,
    source_reports_count: int = 0,
) -> ActiveCompanyTemplateRecord:
    return ActiveCompanyTemplateRecord(
        current_template_id=uuid4(),
        structure=structure,
        created_at=FIXED_TEMPLATE_CREATED_AT,
        version=version,
        source_reports_count=source_reports_count,
    )


def test_resolve_template_company_state_returns_not_configured() -> None:
    result = status_resolver.resolve_template_company_state(None)

    assert result.status == "not_configured"


def test_resolve_template_company_state_returns_active_template() -> None:
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )
    result = status_resolver.resolve_template_company_state(build_active_template(structure))

    assert result.status == "active"
    assert result.sections == structure.sections


def test_resolve_template_company_state_returns_active_with_source_count() -> None:
    active = build_active_template(source_reports_count=5)

    result = status_resolver.resolve_template_company_state(active)

    assert result.status == "active"
    assert result.source_reports_count == 5
