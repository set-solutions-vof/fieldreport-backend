from typing import Annotated

from fastapi import APIRouter, Depends

from src.http.v1.request.report import ReportSectionUpdateRequest
from src.http.v1.response.report import (
    ReportDetailResponse,
    ReportSectionResponse,
    ReportSummaryResponse,
    report_detail_response,
    report_section_response,
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
    report_detail = await reports.get_report_detail(report_id, current_user)

    return report_detail_response(report_detail)


@router.patch("/{report_id}/sections/{section_id}")
async def update_report_section(
    report_id: str,
    section_id: str,
    request_body: ReportSectionUpdateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ReportSectionResponse:
    section = await reports.update_report_section(
        report_id,
        section_id,
        current_user,
        request_body.field_expert_content,
        request_body.is_approved,
    )

    return report_section_response(section)
