from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportEvidenceItem,
    ReportEvidenceSource,
    ReportSection,
    ReportSummary,
)
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import ActiveCompanyTemplateRecord
from src.services import reports as reports_service


def build_report_summary(company_id: UUID) -> ReportSummary:
    return ReportSummary(
        id=uuid4(),
        company_id=company_id,
        status="draft",
        client_name="ACME",
        address="Main Street 1",
        inspection_date=datetime(2026, 5, 8, 12, 30, tzinfo=UTC),
        inspector_name="Jeroen van Dijk",
    )


async def test_list_reports_for_user_returns_repository_reports() -> None:
    current_user = CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="demo@fieldreport.local",
        name="Demo User",
        role="admin",
    )
    report_summaries = [
        build_report_summary(current_user.company_id),
        build_report_summary(current_user.company_id).model_copy(update={"status": "approved"}),
    ]

    with patch.object(
        reports_service.report_queries,
        "list_report_summaries_by_company_id",
        AsyncMock(return_value=report_summaries),
    ) as list_reports:
        result = await reports_service.list_reports_for_user(current_user)

    assert result == report_summaries
    list_reports.assert_awaited_once_with(str(current_user.company_id))


async def test_get_report_detail_returns_evidence_centric_items() -> None:
    current_user = CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="demo@fieldreport.local",
        name="Demo User",
        role="admin",
    )
    report_id = uuid4()
    report = ReportDetail(
        id=report_id,
        status="draft",
        client_name="ACME",
        address="Main Street 1",
        inspection_date=datetime(2026, 5, 8, 12, 30, tzinfo=UTC),
        inspector_name="Jeroen van Dijk",
        sections=[],
    )
    shared_transcription_segment_id = uuid4()
    shared_image_analysis_id = uuid4()
    first_unique_segment_id = uuid4()
    first_capture_time = datetime(2026, 5, 8, 12, 30, 20, tzinfo=UTC)
    sections = [
        ReportDetailSection(
            id=uuid4(),
            section_id="bevindingen",
            label="Bevindingen",
            generated_content="Draft",
            reviewed_content=None,
            approved=False,
            confidence_level="high",
            confidence_score=0.95,
            evidence_item_ids=[shared_image_analysis_id, shared_transcription_segment_id],
        ),
        ReportDetailSection(
            id=uuid4(),
            section_id="advies",
            label="Advies",
            generated_content="Advice",
            reviewed_content=None,
            approved=False,
            confidence_level="medium",
            confidence_score=0.71,
            evidence_item_ids=[
                shared_transcription_segment_id,
                first_unique_segment_id,
                shared_image_analysis_id,
            ],
        ),
    ]
    evidence_items = [
        ReportEvidenceItem(
            id=first_unique_segment_id,
            evidence_type="transcription_segment",
            timeline_seconds=5.0,
            start_seconds=5.0,
            end_seconds=8.0,
            captured_at=None,
            content_summary="Opening note",
        ),
        ReportEvidenceItem(
            id=shared_transcription_segment_id,
            evidence_type="transcription_segment",
            timeline_seconds=12.0,
            start_seconds=12.0,
            end_seconds=15.0,
            captured_at=None,
            content_summary="Moisture mentioned",
        ),
        ReportEvidenceItem(
            id=shared_image_analysis_id,
            evidence_type="image_analysis",
            timeline_seconds=20.0,
            start_seconds=None,
            end_seconds=None,
            captured_at=first_capture_time,
            content_summary="Thermal image",
        ),
    ]

    template_sections_by_id = {
        "bevindingen": TemplateSection(
            id="bevindingen", label="Bevindingen", render_type="text_block"
        ),
        "advies": TemplateSection(id="advies", label="Advies", render_type="text_block"),
    }

    with (
        patch.object(
            reports_service.report_queries,
            "get_report_by_id",
            AsyncMock(return_value=report),
        ) as get_report,
        patch.object(
            reports_service,
            "load_report_detail_sections",
            AsyncMock(return_value=(sections, evidence_items)),
        ) as get_report_sections,
        patch.object(
            reports_service,
            "load_template_sections_by_id",
            AsyncMock(return_value=template_sections_by_id),
        ),
    ):
        result = await reports_service.get_report_detail(str(report_id), current_user)

    assert result.sections == sections
    assert result.evidence_items == evidence_items
    get_report.assert_awaited_once_with(str(report_id), str(current_user.company_id))
    get_report_sections.assert_awaited_once_with(str(report_id))


async def test_load_template_sections_by_id_returns_sections_by_id() -> None:
    company_id = uuid4()
    section = TemplateSection(id="advies", label="Advies", render_type="text_block")
    company_template = ActiveCompanyTemplateRecord(
        current_template_id=uuid4(),
        structure=TemplateStructure(sections=[section]),
    )

    with patch.object(
        reports_service.template_queries,
        "fetch_active_company_template",
        AsyncMock(return_value=company_template),
    ) as fetch_template:
        result = await reports_service.load_template_sections_by_id(str(company_id))

    assert result == {"advies": section}
    fetch_template.assert_awaited_once_with(str(company_id))


async def test_update_report_section_returns_repository_section() -> None:
    current_user = CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="demo@fieldreport.local",
        name="Demo User",
        role="inspector",
    )
    report_id = uuid4()
    section_id = uuid4()
    section = ReportSection(
        id=section_id,
        section_id="advies",
        label="Advies",
        generated_content="Advice",
        reviewed_content="Updated advice",
        approved=True,
        confidence_level="medium",
        confidence_score=0.72,
        evidence_sources=[
            ReportEvidenceSource(
                type="image",
                start_seconds=None,
                end_seconds=None,
                captured_at=None,
                content_summary="Image summary",
            )
        ],
    )

    with (
        patch.object(
            reports_service.report_queries,
            "update_report_section",
            AsyncMock(return_value=section),
        ) as update_section,
        patch.object(
            reports_service,
            "load_template_sections_by_id",
            AsyncMock(
                return_value={
                    "advies": TemplateSection(id="advies", label="Advies", render_type="text_block")
                }
            ),
        ),
    ):
        result = await reports_service.update_report_section(
            str(report_id),
            str(section_id),
            current_user,
            "Updated advice",
            True,
        )

    assert result == section
    update_section.assert_awaited_once_with(
        str(report_id),
        str(section_id),
        str(current_user.company_id),
        "Updated advice",
        True,
    )
