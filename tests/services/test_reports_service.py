from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from src.models.auth.authentication import CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportDetailSection,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
    ReportTimelineItem,
)
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
        reports_service.report_repository,
        "list_report_summaries_by_company_id",
        AsyncMock(return_value=report_summaries),
    ) as list_reports:
        result = await reports_service.list_reports_for_user(current_user)

    assert result == report_summaries
    list_reports.assert_awaited_once_with(str(current_user.company_id))


async def test_get_report_detail_returns_source_centric_timeline_items() -> None:
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
            section_key="bevindingen",
            ai_draft="Draft",
            field_expert_content=None,
            is_approved=False,
            confidence_level="high",
            confidence_score=0.95,
            source_item_ids=[shared_image_analysis_id, shared_transcription_segment_id],
        ),
        ReportDetailSection(
            id=uuid4(),
            section_key="advies",
            ai_draft="Advice",
            field_expert_content=None,
            is_approved=False,
            confidence_level="medium",
            confidence_score=0.71,
            source_item_ids=[
                shared_transcription_segment_id,
                first_unique_segment_id,
                shared_image_analysis_id,
            ],
        ),
    ]
    timeline_items = [
        ReportTimelineItem(
            id=first_unique_segment_id,
            source_type="transcription_segment",
            timeline_offset_seconds=5.0,
            start_seconds=5.0,
            end_seconds=8.0,
            captured_at=None,
            content_summary="Opening note",
        ),
        ReportTimelineItem(
            id=shared_transcription_segment_id,
            source_type="transcription_segment",
            timeline_offset_seconds=12.0,
            start_seconds=12.0,
            end_seconds=15.0,
            captured_at=None,
            content_summary="Moisture mentioned",
        ),
        ReportTimelineItem(
            id=shared_image_analysis_id,
            source_type="image_analysis",
            timeline_offset_seconds=20.0,
            start_seconds=None,
            end_seconds=None,
            captured_at=first_capture_time,
            content_summary="Thermal image",
        ),
    ]

    with (
        patch.object(
            reports_service.report_repository,
            "get_report_by_id",
            AsyncMock(return_value=report),
        ) as get_report,
        patch.object(
            reports_service.report_repository,
            "get_report_detail_sections",
            AsyncMock(return_value=(sections, timeline_items)),
        ) as get_report_sections,
    ):
        result = await reports_service.get_report_detail(str(report_id), current_user)

    assert result.sections == sections
    assert result.timeline_items == timeline_items
    get_report.assert_awaited_once_with(str(report_id), str(current_user.company_id))
    get_report_sections.assert_awaited_once_with(str(report_id))


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
        section_key="advies",
        ai_draft="Advice",
        field_expert_content="Updated advice",
        is_approved=True,
        confidence_level="medium",
        confidence_score=0.72,
        sources=[
            ReportSectionSource(
                type="image",
                timestamp_start=None,
                timestamp_end=None,
                capture_time=None,
                content_summary="Image summary",
            )
        ],
    )

    with patch.object(
        reports_service.report_repository,
        "update_report_section",
        AsyncMock(return_value=section),
    ) as update_section:
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
