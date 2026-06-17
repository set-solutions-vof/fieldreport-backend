from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import Response

from src.exceptions import InspectionPhotoNotFound, InvalidMetadataFormat, MissingMetadataKeys
from src.http.v1.request.inspection import CreateInspectionRequest
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import inspections

router = APIRouter(tags=["Inspections"])


@router.post(
    "/api/v1/inspections",
    response_model=CreateInspectionResponse,
    status_code=status.HTTP_201_CREATED,
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
    except (InvalidMetadataFormat, MissingMetadataKeys) as error:
        raise HTTPException(status_code=422, detail=error.detail) from error


@router.get("/api/v1/inspections/photos/{key:path}", tags=["Inspections"])
async def get_inspection_photo(
    key: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    try:
        data, content_type = await inspections.get_inspection_photo(
            str(current_user.company_id),
            key,
        )
    except InspectionPhotoNotFound:
        raise HTTPException(status_code=404, detail="Photo not found")

    return Response(content=data, media_type=content_type)
