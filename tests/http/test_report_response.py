from datetime import UTC, datetime
from uuid import uuid4

from src.http.v1.response.report import (
    EvidenceItemResponse,
    EvidenceSourceResponse,
    ReportDetailResponse,
    report_detail_response,
)
from src.models.reports.report import ReportDetail, ReportDetailSection


def test_evidence_source_response_serializes_missing_captured_at() -> None:
    response = EvidenceSourceResponse(
        type="audio",
        start_seconds=1.0,
        end_seconds=2.0,
        captured_at=None,
        content_summary="Audio summary",
    )

    assert response.model_dump(mode="json")["captured_at"] is None


def test_timeline_item_response_serializes_missing_captured_at() -> None:
    response = EvidenceItemResponse(
        id=uuid4(),
        evidence_type="transcription_segment",
        timeline_seconds=1.0,
        start_seconds=1.0,
        end_seconds=2.0,
        captured_at=None,
        content_summary="Audio summary",
    )

    assert response.model_dump(mode="json")["captured_at"] is None


def test_report_detail_response_serializes_missing_updated_at() -> None:
    response = ReportDetailResponse(
        id=uuid4(),
        status="draft",
        client_name="ACME",
        address="Main Street 1",
        inspection_date=datetime(2026, 5, 8, 12, 30, tzinfo=UTC),
        inspector_name="Jeroen van Dijk",
        updated_at=None,
        sections=[],
        evidence_items=[],
    )

    assert response.model_dump(mode="json")["updated_at"] is None


def test_report_detail_response_serializes_section_template_metadata() -> None:
    report_id = uuid4()
    section_id = uuid4()
    report = ReportDetail(
        id=report_id,
        status="draft",
        client_name="ACME",
        address="Main Street 1",
        inspection_date=datetime(2026, 5, 8, 12, 30, tzinfo=UTC),
        inspector_name="Jeroen van Dijk",
        sections=[
            ReportDetailSection(
                id=section_id,
                section_id="meetresultaten",
                label="Meetresultaten",
                generated_content="Visuele inspectie: Geen lekkage.",
                reviewed_content=None,
                approved=False,
                confidence_level="high",
                confidence_score=0.91,
                render_type="measurement_table",
                fields=["Visuele inspectie"],
                groups=[
                    {
                        "id": "algemene_inspectie",
                        "label": "Algemene inspectie",
                        "fields": ["Visuele inspectie"],
                    }
                ],
                evidence_item_ids=[],
            )
        ],
    )

    response = report_detail_response(report).model_dump(mode="json")

    assert response["sections"][0]["render_type"] == "measurement_table"
    assert response["sections"][0]["fields"] == ["Visuele inspectie"]
    assert response["sections"][0]["groups"] == [
        {
            "id": "algemene_inspectie",
            "label": "Algemene inspectie",
            "fields": ["Visuele inspectie"],
        }
    ]
