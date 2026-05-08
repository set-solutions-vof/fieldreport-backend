from typing import Annotated

from fastapi import APIRouter, Depends

from src.http.v1.response.report import ReportSummaryResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import reports

router = APIRouter(prefix="/api/v1/reports")


@router.get("")
async def get_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ReportSummaryResponse]:
    report_summaries = await reports.list_reports_for_user(current_user)

    return [
        ReportSummaryResponse(
            id=str(report_summary.id),
            company_id=str(report_summary.company_id),
            status=report_summary.status,
        )
        for report_summary in report_summaries
    ]
