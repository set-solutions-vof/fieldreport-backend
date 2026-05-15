from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.db.template_mapper import map_company_template, map_template_analysis_job
from src.models.templates.configuration import (
    StoredTemplateStructure,
    TemplateSection,
    parse_stored_template_structure,
)
from src.models.templates.records import CompanyTemplateRecord, TemplateAnalysisJobRecord


def test_parse_stored_template_structure_returns_existing_model() -> None:
    structure = StoredTemplateStructure(sections=[])

    assert parse_stored_template_structure(structure) is structure


def test_parse_stored_template_structure_parses_json_string() -> None:
    structure = parse_stored_template_structure(
        '{"sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}]}'
    )

    assert structure == StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )


def test_parse_stored_template_structure_rejects_unsupported_value() -> None:
    with pytest.raises(TypeError, match="Unsupported structure value"):
        parse_stored_template_structure(42)


def test_map_company_template_parses_record() -> None:
    template_id = uuid4()

    record = map_company_template(
        {
            "template_id": template_id,
            "structure": '{"sections": []}',
        }
    )

    assert record == CompanyTemplateRecord(
        template_id=template_id,
        structure=StoredTemplateStructure(sections=[]),
    )


def test_map_template_analysis_job_parses_record() -> None:
    job_id = uuid4()
    company_id = uuid4()
    created_at = datetime.now(UTC)

    record = map_template_analysis_job(
        {
            "id": job_id,
            "company_id": company_id,
            "template_id": None,
            "status": "queued",
            "reports_count": 2,
            "structure": None,
            "error_message": None,
            "created_at": created_at,
        }
    )

    assert record == TemplateAnalysisJobRecord(
        id=job_id,
        company_id=company_id,
        template_id=None,
        status="queued",
        reports_count=2,
        created_at=created_at,
    )
