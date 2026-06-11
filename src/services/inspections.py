from datetime import date
from uuid import uuid4

from azure.core.exceptions import ResourceNotFoundError
from pydantic import ValidationError

from src.db.connection import get_database
from src.db.inspection import queries
from src.db.template.queries import fetch_active_company_template
from src.exceptions import InspectionPhotoNotFound, InvalidMetadataFormat, MissingMetadataKeys
from src.http.v1.request.inspection import CreateInspectionRequest
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.reports.metadata import ReportMetadata
from src.storage import blob
from src.utils.storage import upload_files, upload_images


async def create_inspection(
    company_id: str,
    user_id: str,
    request: CreateInspectionRequest,
) -> CreateInspectionResponse:
    company_template = await fetch_active_company_template(company_id)

    try:
        metadata = ReportMetadata.model_validate_json(request.metadata)
    except ValidationError as error:
        raise InvalidMetadataFormat() from error
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

    async with get_database().acquire() as connection:
        await queries.insert_inspection(
            connection,
            inspection_id,
            company_id,
            user_id,
            template_id,
            metadata,
            request.extra_context or "",
            date.today(),
        )

        for audio_file, storage_key in zip(request.audio_files, audio_storage_keys, strict=True):
            await queries.insert_inspection_audio_file(
                connection,
                inspection_id,
                storage_key,
                audio_file.filename or "",
            )

        for photo_file, storage_key in zip(request.photo_files, photo_storage_keys, strict=True):
            await queries.insert_inspection_photo_file(
                connection,
                inspection_id,
                storage_key,
                photo_file.filename or "",
            )

        await queries.insert_report(
            connection,
            report_id,
            inspection_id,
            company_id,
            template_id,
        )

    return CreateInspectionResponse(report_id=report_id, status="generating")


async def get_inspection_photo(company_id: str, key: str) -> tuple[bytes, str]:
    belongs_to_company = await queries.inspection_photo_belongs_to_company(company_id, key)

    if not belongs_to_company:
        raise InspectionPhotoNotFound(key)

    try:
        return await blob.download_file("inspections", key)
    except ResourceNotFoundError:
        raise InspectionPhotoNotFound(key)
