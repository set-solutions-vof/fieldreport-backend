from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Form, HTTPException

from src.db import inspection_queries, template_queries
from src.http.v1.request.inspection import CreateInspectionRequest
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.auth.authentication import CurrentUser
from src.models.reports.metadata import ReportMetadata
from src.security.authentication import get_current_user
from src.storage import inspection_file_storage

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
    company_template = await template_queries.fetch_active_company_template(
        str(current_user.company_id)
    )

    metadata = ReportMetadata.model_validate_json(request_body.metadata)
    metadata_values = metadata.model_dump()
    missing_metadata_keys = [
        metadata_field.key
        for metadata_field in company_template.structure.metadata_fields
        if metadata_field.required and metadata_field.key not in metadata_values
    ]

    if missing_metadata_keys:
        raise HTTPException(status_code=422, detail={"missing_keys": missing_metadata_keys})

    inspection_id = str(uuid4())
    report_id = str(uuid4())
    audio_storage_keys, photo_storage_keys = await inspection_file_storage.store_inspection_files(
        str(current_user.company_id),
        inspection_id,
        request_body.audio_files,
        request_body.photo_files,
    )
    template_id = str(company_template.current_template_id)

    await inspection_queries.insert_inspection(
        inspection_id,
        str(current_user.company_id),
        str(current_user.id),
        template_id,
        metadata,
        request_body.extra_context or "",
        date.today(),
    )

    for audio_file, storage_key in zip(request_body.audio_files, audio_storage_keys, strict=True):
        await inspection_queries.insert_inspection_audio_file(
            inspection_id,
            storage_key,
            audio_file.filename or "",
        )

    for photo_file, storage_key in zip(request_body.photo_files, photo_storage_keys, strict=True):
        await inspection_queries.insert_inspection_photo_file(
            inspection_id,
            storage_key,
            photo_file.filename or "",
        )

    await inspection_queries.insert_report(
        report_id,
        inspection_id,
        str(current_user.company_id),
        template_id,
    )

    return CreateInspectionResponse(report_id=report_id, status="generating")
