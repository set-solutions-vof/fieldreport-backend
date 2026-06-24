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
        first_name="Inspector",
        last_name="",
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


async def test_retry_report_returns_no_content() -> None:
    current_user = build_current_user()
    report_id = uuid4()

    with patch.object(
        reports.reports,
        "retry_failed_report",
        AsyncMock(),
    ) as retry_report:
        response = await reports.retry_report(report_id, current_user)

    assert response.status_code == 204
    retry_report.assert_awaited_once_with(str(report_id), current_user)


async def test_retry_report_returns_not_found() -> None:
    current_user = build_current_user()

    with patch.object(
        reports.reports,
        "retry_failed_report",
        AsyncMock(side_effect=ReportNotFound("report-id")),
    ):
        try:
            await reports.retry_report(uuid4(), current_user)
        except HTTPException as error:
            assert error.status_code == 404
            assert error.detail == "Report not found"
        else:
            raise AssertionError("Expected HTTPException")


async def test_retry_report_returns_conflict_for_non_failed_report() -> None:
    current_user = build_current_user()

    with patch.object(
        reports.reports,
        "retry_failed_report",
        AsyncMock(side_effect=ValueError("wrong status")),
    ):
        try:
            await reports.retry_report(uuid4(), current_user)
        except HTTPException as error:
            assert error.status_code == 409
            assert error.detail == "Report can only be retried when failed"
        else:
            raise AssertionError("Expected HTTPException")


async def test_export_report_returns_422_when_sections_not_all_approved() -> None:
    current_user = build_current_user()

    with patch.object(reports, "check_all_sections_approved", AsyncMock(return_value=False)):
        try:
            await reports.export_report(uuid4(), current_user)
        except HTTPException as error:
            assert error.status_code == 422
        else:
            raise AssertionError("Expected HTTPException")


async def test_export_report_returns_pdf_bytes_when_approved() -> None:
    from unittest.mock import MagicMock
    from tests.db.sqlalchemy_fakes import FakeResult, build_connection

    current_user = build_current_user()
    report_id = uuid4()
    inspection_id = uuid4()
    pdf_bytes = b"%%PDF fake"

    connection = build_connection(
        results=[
            FakeResult(row={"inspection_id": str(inspection_id)}),
            FakeResult(row=None),
        ]
    )
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(reports, "check_all_sections_approved", AsyncMock(return_value=True)),
        patch.object(reports, "render_report_to_pdf", AsyncMock(return_value=pdf_bytes)),
        patch.object(reports, "upload_file", AsyncMock()),
        patch.object(reports, "get_database", return_value=pool),
    ):
        response = await reports.export_report(report_id, current_user)

    assert response.status_code == 200
    assert response.body == pdf_bytes
    assert response.media_type == "application/pdf"
    assert f"report-{report_id}.pdf" in response.headers["content-disposition"]
