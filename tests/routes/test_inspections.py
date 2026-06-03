from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from src.http.v1.request.inspection import CreateInspectionRequest
from src.models.auth.authentication import CurrentUser
from src.models.reports.metadata import ReportMetadata
from src.models.templates.domain import (
    TemplateScalarMetadataField,
    TemplateSelectMetadataField,
    TemplateStructure,
)
from src.models.templates.records import ActiveCompanyTemplateRecord
from src.routes import inspections


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="FieldReport",
        email="inspector@example.com",
        name="Inspector",
        role="inspector",
    )


async def test_create_inspection_stores_files_and_creates_report() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    audio_file = UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))
    photo_file = UploadFile(filename="photo.jpg", file=BytesIO(b"photo"))

    with (
        patch(
            "src.routes.inspections.template_queries.fetch_active_company_template",
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
        patch(
            "src.routes.inspections.inspection_file_storage.store_inspection_files",
            AsyncMock(return_value=(["/tmp/audio.m4a"], ["/tmp/photo.jpg"])),
        ) as store_files,
        patch(
            "src.routes.inspections.inspection_queries.insert_inspection",
            AsyncMock(),
        ) as insert_inspection,
        patch(
            "src.routes.inspections.inspection_queries.insert_inspection_audio_file",
            AsyncMock(),
        ) as insert_audio,
        patch(
            "src.routes.inspections.inspection_queries.insert_inspection_photo_file",
            AsyncMock(),
        ) as insert_photo,
        patch(
            "src.routes.inspections.inspection_queries.insert_report",
            AsyncMock(),
        ) as insert_report,
    ):
        response = await inspections.create_inspection(
            CreateInspectionRequest(
                metadata=(
                    '{"type_onderzoek":"Lekdetectie","type_klant":"Zakelijk",'
                    '"naam_opdrachtgever":"ACME","adres_schadeadres":"Main Street 1"}'
                ),
                extra_context="Extra",
                audio_files=[audio_file],
                photo_files=[photo_file],
            ),
            current_user,
        )

    assert response.status == "generating"
    assert response.report_id
    store_files.assert_awaited_once()
    inspection_id = insert_inspection.await_args.args[0]
    assert insert_inspection.await_args.args[4:6] == (
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
    insert_audio.assert_awaited_once_with(inspection_id, "/tmp/audio.m4a", "audio.m4a")
    insert_photo.assert_awaited_once_with(inspection_id, "/tmp/photo.jpg", "photo.jpg")
    insert_report.assert_awaited_once()


async def test_create_inspection_returns_missing_required_metadata_keys() -> None:
    current_user = build_current_user()

    with (
        patch(
            "src.routes.inspections.template_queries.fetch_active_company_template",
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
        ),
        patch(
            "src.routes.inspections.inspection_file_storage.store_inspection_files",
            AsyncMock(),
        ) as store_files,
    ):
        try:
            await inspections.create_inspection(
                CreateInspectionRequest(
                    metadata="{}",
                    audio_files=[UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))],
                ),
                current_user,
            )
        except HTTPException as error:
            assert error.status_code == 422
            assert error.detail == {"missing_keys": ["naam_opdrachtgever"]}
        else:
            raise AssertionError("Expected HTTPException")

    store_files.assert_not_awaited()
