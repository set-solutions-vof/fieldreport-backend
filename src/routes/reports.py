from typing import Annotated

from fastapi import APIRouter, Depends

from src.http.v1.response.report import ReportSummaryResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user

router = APIRouter(prefix="/api/v1/reports")


@router.get("")
async def get_reports(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[ReportSummaryResponse]:
    return [
        ReportSummaryResponse(id="demo-report", company_id=str(current_user.company_id), status="draft")
    ]
