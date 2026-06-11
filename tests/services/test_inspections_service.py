from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from azure.core.exceptions import ResourceNotFoundError
from starlette.datastructures import UploadFile

from src.exceptions import InspectionPhotoNotFound, InvalidMetadataFormat, MissingMetadataKeys
from src.http.v1.request.inspection import CreateInspectionRequest
from src.models.reports.metadata import ReportMetadata
from src.models.templates.domain import (
    TemplateScalarMetadataField,
    TemplateSelectMetadataField,
    TemplateStructure,
)
from src.models.templates.records import ActiveCompanyTemplateRecord
from src.services import inspections as inspections_service


async def test_create_inspection_stores_files_and_creates_report() -> None:
    company_id = str(uuid4())
    user_id = str(uuid4())
    template_id = uuid4()
    audio_file = UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))
    photo_file = UploadFile(filename="photo.jpg", file=BytesIO(b"photo"))
    connection = MagicMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "src.services.inspections.fetch_active_company_template",
            AsyncMock(
                return_value=ActiveCompanyTemplateRecord(
                    current_template_id=template_id,
                    structure=TemplateStructure(
                        metadata_fields=[
                            TemplateSelectMetadataField(
                                key="type_onderzoek",
                                label="Type onderzoek",
                                type="select",
                                options=["Lekdetectie"],
                                required=True,
                            ),
                            TemplateSelectMetadataField(
                                key="type_klant",
                                label="Type klant",
                                type="select",
                                options=["Zakelijk"],
                                required=True,
                            ),
                            TemplateScalarMetadataField(
                                key="naam_opdrachtgever",
                                label="Naam opdrachtgever",
                                type="text",
                                required=True,
                            ),
                            TemplateScalarMetadataField(
                                key="adres_schadeadres",
                                label="Adres schadeadres",
                                type="text",
                                required=True,
                            ),
                        ],
                        sections=[],
                    ),
                )
            ),
        ),
        patch.object(
            inspections_service,
            "upload_files",
            AsyncMock(return_value=["https://storage.example/audio"]),
        ) as upload_audio_files,
        patch.object(
            inspections_service,
            "upload_images",
            AsyncMock(return_value=["https://storage.example/photo"]),
        ) as upload_photo_files,
        patch.object(
            inspections_service.queries,
            "insert_inspection",
            AsyncMock(),
        ) as insert_inspection,
        patch.object(
            inspections_service.queries,
            "insert_inspection_audio_file",
            AsyncMock(),
        ) as insert_audio,
        patch.object(
            inspections_service.queries,
            "insert_inspection_photo_file",
            AsyncMock(),
        ) as insert_photo,
        patch.object(
            inspections_service.queries,
            "insert_report",
            AsyncMock(),
        ) as insert_report,
        patch.object(inspections_service, "get_database", MagicMock(return_value=pool)),
    ):
        response = await inspections_service.create_inspection(
            company_id,
            user_id,
            CreateInspectionRequest(
                metadata=(
                    '{"type_onderzoek":"Lekdetectie","type_klant":"Zakelijk",'
                    '"naam_opdrachtgever":"ACME","adres_schadeadres":"Main Street 1"}'
                ),
                extra_context="Extra",
                audio_files=[audio_file],
                photo_files=[photo_file],
            ),
        )

    assert response.status == "generating"
    assert response.report_id
    upload_audio_files.assert_awaited_once()
    upload_photo_files.assert_awaited_once()
    inspection_id = insert_inspection.await_args.args[1]
    assert insert_inspection.await_args.args[5:7] == (
        ReportMetadata.model_validate(
            {
                "type_onderzoek": "Lekdetectie",
                "type_klant": "Zakelijk",
                "naam_opdrachtgever": "ACME",
                "adres_schadeadres": "Main Street 1",
            }
        ),
        "Extra",
    )
    insert_audio.assert_awaited_once()
    assert insert_audio.await_args.args[1] == inspection_id
    assert insert_audio.await_args.args[3] == "audio.m4a"
    insert_photo.assert_awaited_once()
    assert insert_photo.await_args.args[1] == inspection_id
    assert insert_photo.await_args.args[3] == "photo.jpg"
    insert_report.assert_awaited_once()


async def test_create_inspection_raises_for_invalid_metadata_format() -> None:
    with patch(
        "src.services.inspections.fetch_active_company_template",
        AsyncMock(
            return_value=ActiveCompanyTemplateRecord(
                current_template_id=uuid4(),
                structure=TemplateStructure(metadata_fields=[], sections=[]),
            )
        ),
    ):
        with pytest.raises(InvalidMetadataFormat):
            await inspections_service.create_inspection(
                str(uuid4()),
                str(uuid4()),
                CreateInspectionRequest(
                    metadata="{",
                    audio_files=[UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))],
                ),
            )


async def test_create_inspection_raises_for_missing_required_metadata_keys() -> None:
    with patch(
        "src.services.inspections.fetch_active_company_template",
        AsyncMock(
            return_value=ActiveCompanyTemplateRecord(
                current_template_id=uuid4(),
                structure=TemplateStructure(
                    metadata_fields=[
                        TemplateScalarMetadataField(
                            key="naam_opdrachtgever",
                            label="Naam opdrachtgever",
                            type="text",
                            required=True,
                        )
                    ],
                    sections=[],
                ),
            )
        ),
    ):
        with pytest.raises(MissingMetadataKeys) as error:
            await inspections_service.create_inspection(
                str(uuid4()),
                str(uuid4()),
                CreateInspectionRequest(
                    metadata="{}",
                    audio_files=[UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))],
                ),
            )

    assert error.value.keys == ["naam_opdrachtgever"]


async def test_get_inspection_photo_returns_blob() -> None:
    with (
        patch.object(
            inspections_service.queries,
            "inspection_photo_belongs_to_company",
            AsyncMock(return_value=True),
        ),
        patch.object(
            inspections_service.blob,
            "download_file",
            AsyncMock(return_value=(b"photo", "image/jpeg")),
        ) as download,
    ):
        data, content_type = await inspections_service.get_inspection_photo(
            "company-id",
            "company-id/inspection-id/photos/photo.jpg",
        )

    assert data == b"photo"
    assert content_type == "image/jpeg"
    download.assert_awaited_once_with(
        "inspections",
        "company-id/inspection-id/photos/photo.jpg",
    )


async def test_get_inspection_photo_raises_when_not_in_company() -> None:
    with patch.object(
        inspections_service.queries,
        "inspection_photo_belongs_to_company",
        AsyncMock(return_value=False),
    ):
        with pytest.raises(InspectionPhotoNotFound):
            await inspections_service.get_inspection_photo(
                "company-id",
                "other-company/inspection-id/photos/photo.jpg",
            )


async def test_get_inspection_photo_raises_when_blob_is_missing() -> None:
    with (
        patch.object(
            inspections_service.queries,
            "inspection_photo_belongs_to_company",
            AsyncMock(return_value=True),
        ),
        patch.object(
            inspections_service.blob,
            "download_file",
            AsyncMock(side_effect=ResourceNotFoundError("missing")),
        ),
    ):
        with pytest.raises(InspectionPhotoNotFound):
            await inspections_service.get_inspection_photo(
                "company-id",
                "company-id/inspection-id/photos/photo.jpg",
            )
