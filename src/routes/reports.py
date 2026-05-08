from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.http.v1.response.report import (
    ReportDetailResponse,
    ReportSummaryResponse,
    report_detail_response,
    report_summary_responses,
)
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import reports

router = APIRouter(prefix="/api/v1/reports")


@router.get("")
async def get_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ReportSummaryResponse]:
    report_summaries = await reports.list_reports_for_user(current_user)

    return report_summary_responses(report_summaries)


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ReportDetailResponse:
    try:
        report_detail = await reports.get_report_detail(report_id, current_user)
    except reports.ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")

    return report_detail_response(report_detail)
