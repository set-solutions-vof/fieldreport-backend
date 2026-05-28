from datetime import UTC, datetime
from uuid import uuid4

from src.db.template_mapper import (
    map_active_company_template,
    map_optional_active_company_template,
    map_template_analysis_job,
    parse_template_structure,
)
from src.models.templates.domain import (
    TemplateSection,
    TemplateSectionGroup,
    TemplateStructure,
)
from src.models.templates.records import (
    ActiveCompanyTemplateRecord,
    TemplateAnalysisJobRecord,
)


def test_parse_template_structure_parses_json_string() -> None:
    structure = parse_template_structure(
        '{"sections": [{"id": "summary", "label": "Summary", "render_type": "text_block"}]}'
    )

    assert structure == TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )


def test_parse_template_structure_parses_groups() -> None:
    structure = parse_template_structure(
        """
        {
          "sections": [
            {
              "id": "meetresultaten",
              "label": "Meetresultaten",
              "order": 2,
              "render_type": "measurement_table",
              "fields": ["Visuele inspectie", "Thermografie", "Druktest"],
              "found_in": 3,
              "groups": [
                {
                  "id": "algemene_inspectie",
                  "label": "Algemene inspectie schadebeeld/ leidingwerk",
                  "fields": ["Visuele inspectie", "Thermografie"]
                },
                {
                  "id": "waterleidingen",
                  "label": "Waterleidingen",
                  "fields": ["Druktest"]
                }
              ]
            }
          ]
        }
        """
    )

    assert structure == TemplateStructure(
        sections=[
            TemplateSection(
                id="meetresultaten",
                label="Meetresultaten",
                order=2,
                render_type="measurement_table",
                fields=["Visuele inspectie", "Thermografie", "Druktest"],
                found_in=3,
                groups=[
                    TemplateSectionGroup(
                        id="algemene_inspectie",
                        label="Algemene inspectie schadebeeld/ leidingwerk",
                        fields=["Visuele inspectie", "Thermografie"],
                    ),
                    TemplateSectionGroup(
                        id="waterleidingen",
                        label="Waterleidingen",
                        fields=["Druktest"],
                    ),
                ],
            )
        ]
    )


def test_map_optional_active_company_template_returns_none_without_template_id() -> None:
    record = map_optional_active_company_template({"current_template_id": None, "structure": None})

    assert record is None


def test_map_optional_active_company_template_parses_record() -> None:
    template_id = uuid4()

    record = map_optional_active_company_template(
        {
            "current_template_id": template_id,
            "structure": '{"sections": []}',
        }
    )

    assert record == ActiveCompanyTemplateRecord(
        current_template_id=template_id,
        structure=TemplateStructure(sections=[]),
    )


def test_map_active_company_template_parses_record() -> None:
    template_id = uuid4()

    record = map_active_company_template(
        {
            "current_template_id": template_id,
            "structure": '{"sections": []}',
        }
    )

    assert record == ActiveCompanyTemplateRecord(
        current_template_id=template_id,
        structure=TemplateStructure(sections=[]),
    )


def test_map_template_analysis_job_parses_record() -> None:
    job_id = uuid4()
    company_id = uuid4()
    created_at = datetime.now(UTC)

    record = map_template_analysis_job(
        {
            "id": job_id,
            "company_id": company_id,
            "status": "queued",
            "source_reports_count": 2,
            "structure": None,
            "failure_message": None,
            "created_at": created_at,
        }
    )

    assert record == TemplateAnalysisJobRecord(
        id=job_id,
        company_id=company_id,
        status="queued",
        source_reports_count=2,
        structure=TemplateStructure(sections=[]),
        created_at=created_at,
    )
