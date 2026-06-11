from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException

from src.exceptions import ReportNotFound
from src.http.v1.request.report import ReportSectionUpdateRequest
from src.models.auth.authentication import CurrentUser
from src.models.reports.report import ReportDetail, ReportSection
from src.routes import reports


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector@example.com",
        name="Inspector",
        role="inspector",
    )


async def test_get_report_returns_not_found() -> None:
    current_user = build_current_user()

    with patch.object(
        reports.reports,
        "get_report_detail",
        AsyncMock(side_effect=ReportNotFound("report-id")),
    ):
        try:
            await reports.get_report("report-id", current_user)
        except HTTPException as error:
            assert error.status_code == 404
            assert error.detail == "Report not found"
        else:
            raise AssertionError("Expected HTTPException")


async def test_update_report_section_returns_not_found() -> None:
    current_user = build_current_user()

    with patch.object(
        reports.reports,
        "update_report_section",
        AsyncMock(side_effect=ReportNotFound("report-id")),
    ):
        try:
            await reports.update_report_section(
                "report-id",
                "section-id",
                ReportSectionUpdateRequest(reviewed_content=None, approved=True),
                current_user,
            )
        except HTTPException as error:
            assert error.status_code == 404
            assert error.detail == "Report or section not found"
        else:
            raise AssertionError("Expected HTTPException")


async def test_report_routes_return_success_payloads() -> None:
    current_user = build_current_user()
    report_detail = ReportDetail(
        id=uuid4(),
        status="draft",
        metadata={},
        inspection_date=datetime.now(UTC),
        inspector_name="Inspector",
        sections=[],
        evidence_items=[],
    )
    section = ReportSection(
        id=uuid4(),
        section_id="summary",
        label="Summary",
        generated_content="Draft",
        reviewed_content=None,
        approved=True,
        confidence_level="high",
        confidence_score=0.95,
        render_type="text_block",
        fields=None,
        groups=None,
        evidence_sources=[],
    )

    with (
        patch.object(
            reports.reports,
            "get_report_detail",
            AsyncMock(return_value=report_detail),
        ),
        patch.object(
            reports.reports,
            "update_report_section",
            AsyncMock(return_value=section),
        ),
    ):
        detail_response = await reports.get_report("report-id", current_user)
        section_response = await reports.update_report_section(
            "report-id",
            "section-id",
            ReportSectionUpdateRequest(reviewed_content=None, approved=True),
            current_user,
        )

    assert detail_response.id == report_detail.id
    assert section_response.id == section.id
