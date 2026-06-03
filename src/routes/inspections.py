from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException

from src.exceptions import MissingMetadataKeys
from src.http.v1.request.inspection import CreateInspectionRequest
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import inspections

router = APIRouter(tags=["Inspections"])


@router.post(
    "/api/v1/reports",
    response_model=CreateInspectionResponse,
    summary="Create report",
    description="Creates an inspection with audio and photo uploads and starts report generation.",
)
@router.post(
    "/api/v1/inspections",
    response_model=CreateInspectionResponse,
    summary="Create inspection",
    description="Creates an inspection with audio and photo uploads and starts report generation.",
)
async def create_inspection(
    request_body: Annotated[CreateInspectionRequest, Form()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CreateInspectionResponse:
    try:
        return await inspections.create_inspection(
            str(current_user.company_id),
            str(current_user.id),
            request_body,
        )
    except MissingMetadataKeys as error:
        raise HTTPException(status_code=422, detail={"missing_keys": error.keys})
