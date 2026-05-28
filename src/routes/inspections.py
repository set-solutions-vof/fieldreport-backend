from datetime import date
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile

from src.db import inspection_queries, template_queries
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.storage import inspection_file_storage

router = APIRouter(tags=["Inspections"])


@router.post(
    "/api/v1/inspections",
    response_model=CreateInspectionResponse,
    summary="Create inspection",
    description="Creates an inspection with audio and photo uploads and starts report generation.",
)
async def create_inspection(
    address: Annotated[str, Form()],
    inspection_date: Annotated[str, Form()],
    investigation_type: Annotated[str, Form()],
    client_type: Annotated[str, Form()],
    audio_files: Annotated[list[UploadFile], File()],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    reference_number: Annotated[str | None, Form()] = None,
    extra_context: Annotated[str | None, Form()] = None,
    photo_files: Annotated[list[UploadFile], File()] = [],
) -> CreateInspectionResponse:
    company_template = await template_queries.fetch_active_company_template(
        str(current_user.company_id)
    )

    parsed_inspection_date = date.fromisoformat(inspection_date)

    inspection_id = str(uuid4())
    report_id = str(uuid4())
    audio_storage_keys, photo_storage_keys = await inspection_file_storage.store_inspection_files(
        str(current_user.company_id),
        inspection_id,
        audio_files,
        photo_files,
    )
    template_id = str(company_template.current_template_id)

    await inspection_queries.insert_inspection(
        inspection_id,
        str(current_user.company_id),
        str(current_user.id),
        template_id,
        address,
        address,
        investigation_type,
        client_type,
        extra_context or "",
        parsed_inspection_date,
    )

    for audio_file, storage_key in zip(audio_files, audio_storage_keys, strict=True):
        await inspection_queries.insert_inspection_audio_file(
            inspection_id,
            storage_key,
            audio_file.filename or "",
        )

    for photo_file, storage_key in zip(photo_files, photo_storage_keys, strict=True):
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

    return CreateInspectionResponse(report_id=report_id, status="processing")
