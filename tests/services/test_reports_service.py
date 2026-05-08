from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.models.auth.authentication import CurrentUser
from src.models.reports.report import ReportSummary
from src.services import reports as reports_service


async def test_list_reports_for_user_returns_repository_reports() -> None:
    current_user = CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        email="demo@fieldreport.local",
        name="Demo User",
        role="admin",
    )
    report_summaries = [
        ReportSummary(id=uuid4(), company_id=current_user.company_id, status="draft"),
        ReportSummary(id=uuid4(), company_id=current_user.company_id, status="approved"),
    ]

    with patch.object(
        reports_service.report_repository,
        "list_report_summaries_by_company_id",
        AsyncMock(return_value=report_summaries),
    ) as list_reports:
        result = await reports_service.list_reports_for_user(current_user)

    assert result == report_summaries
    list_reports.assert_awaited_once_with(str(current_user.company_id))
