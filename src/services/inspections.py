from datetime import date
from uuid import uuid4

from src.db import inspection_queries, template_queries
from src.exceptions import MissingMetadataKeys
from src.http.v1.request.inspection import CreateInspectionRequest
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.reports.metadata import ReportMetadata
from src.utils.storage import upload_files, upload_images


async def create_inspection(
    company_id: str,
    user_id: str,
    request: CreateInspectionRequest,
) -> CreateInspectionResponse:
    company_template = await template_queries.fetch_active_company_template(company_id)

    metadata = ReportMetadata.model_validate_json(request.metadata)
    metadata_values = metadata.model_dump()
    missing_keys = [
        field.key
        for field in company_template.structure.metadata_fields
        if field.required and field.key not in metadata_values
    ]

    if missing_keys:
        raise MissingMetadataKeys(missing_keys)

    inspection_id = str(uuid4())
    report_id = str(uuid4())
    template_id = str(company_template.current_template_id)

    audio_storage_keys = await upload_files(
        "inspections", f"{company_id}/{inspection_id}/audio", request.audio_files
    )
    photo_storage_keys = await upload_images(
        "inspections", f"{company_id}/{inspection_id}/photos", request.photo_files
    )

    await inspection_queries.insert_inspection(
        inspection_id,
        company_id,
        user_id,
        template_id,
        metadata,
        request.extra_context or "",
        date.today(),
    )

    for audio_file, storage_key in zip(request.audio_files, audio_storage_keys, strict=True):
        await inspection_queries.insert_inspection_audio_file(
            inspection_id,
            storage_key,
            audio_file.filename or "",
        )

    for photo_file, storage_key in zip(request.photo_files, photo_storage_keys, strict=True):
        await inspection_queries.insert_inspection_photo_file(
            inspection_id,
            storage_key,
            photo_file.filename or "",
        )

    await inspection_queries.insert_report(report_id, inspection_id, company_id, template_id)

    return CreateInspectionResponse(report_id=report_id, status="generating")
