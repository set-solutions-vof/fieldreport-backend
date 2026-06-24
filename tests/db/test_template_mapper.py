from datetime import UTC, datetime
from uuid import uuid4

from src.db.template.mapper import (
    map_active_company_template,
    map_optional_active_company_template,
)
from src.models.templates.domain import TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord

FIXED_TEMPLATE_CREATED_AT = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)


def test_map_optional_active_company_template_returns_none_without_template_id() -> None:
    record = map_optional_active_company_template({"current_template_id": None, "structure": None})

    assert record is None


def test_map_optional_active_company_template_parses_record() -> None:
    template_id = uuid4()

    record = map_optional_active_company_template(
        {
            "current_template_id": template_id,
            "structure": '{"sections": []}',
            "created_at": FIXED_TEMPLATE_CREATED_AT,
            "version": 2,
            "source_reports_count": 0,
        }
    )

    assert record == ActiveCompanyTemplateRecord(
        current_template_id=template_id,
        structure=TemplateStructure(sections=[]),
        created_at=FIXED_TEMPLATE_CREATED_AT,
        version=2,
        source_reports_count=0,
    )


def test_map_active_company_template_parses_record() -> None:
    template_id = uuid4()

    record = map_active_company_template(
        {
            "current_template_id": template_id,
            "structure": '{"sections": []}',
            "created_at": FIXED_TEMPLATE_CREATED_AT,
            "version": 1,
            "source_reports_count": 0,
        }
    )

    assert record == ActiveCompanyTemplateRecord(
        current_template_id=template_id,
        structure=TemplateStructure(sections=[]),
        created_at=FIXED_TEMPLATE_CREATED_AT,
        version=1,
        source_reports_count=0,
    )
