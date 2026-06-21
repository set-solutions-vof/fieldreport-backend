from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from starlette.datastructures import UploadFile

from src.exceptions import InspectionPhotoNotFound, InvalidMetadataFormat, MissingMetadataKeys
from src.http.v1.request.inspection import CreateInspectionRequest
from src.http.v1.response.inspection import CreateInspectionResponse
from src.models.auth.authentication import CurrentUser
from src.routes import inspections


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="FieldReport",
        email="inspector@example.com",
        first_name="Inspector",
        last_name="",
        role="inspector",
    )


async def test_create_inspection_stores_files_and_creates_report() -> None:
    current_user = build_current_user()
    audio_file = UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))
    photo_file = UploadFile(filename="photo.jpg", file=BytesIO(b"photo"))
    response_payload = CreateInspectionResponse(
        report_id=str(uuid4()),
        status="generating",
    )

    with patch(
        "src.routes.inspections.inspections.create_inspection",
        AsyncMock(return_value=response_payload),
    ) as create_inspection:
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

    assert response == response_payload
    create_inspection.assert_awaited_once_with(
        str(current_user.company_id),
        str(current_user.id),
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


async def test_create_inspection_returns_missing_required_metadata_keys() -> None:
    current_user = build_current_user()

    with patch(
        "src.routes.inspections.inspections.create_inspection",
        AsyncMock(side_effect=MissingMetadataKeys(["naam_opdrachtgever"])),
    ) as create_inspection:
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

    create_inspection.assert_awaited_once()


async def test_create_inspection_returns_invalid_metadata_format() -> None:
    current_user = build_current_user()

    with patch(
        "src.routes.inspections.inspections.create_inspection",
        AsyncMock(side_effect=InvalidMetadataFormat()),
    ):
        try:
            await inspections.create_inspection(
                CreateInspectionRequest(
                    metadata="{",
                    audio_files=[UploadFile(filename="audio.m4a", file=BytesIO(b"audio"))],
                ),
                current_user,
            )
        except HTTPException as error:
            assert error.status_code == 422
            assert error.detail == "Invalid metadata format"
        else:
            raise AssertionError("Expected HTTPException")


async def test_get_inspection_photo_returns_image_bytes() -> None:
    current_user = build_current_user()
    key = f"{current_user.company_id}/inspection/photo.jpg"

    with patch(
        "src.routes.inspections.inspections.get_inspection_photo",
        AsyncMock(return_value=(b"\xff\xd8\xff", "image/png")),
    ) as get_photo:
        response = await inspections.get_inspection_photo(key, current_user)

    assert response.body == b"\xff\xd8\xff"
    assert response.media_type == "image/png"
    get_photo.assert_awaited_once_with(str(current_user.company_id), key)


async def test_get_inspection_photo_returns_not_found_for_missing_photo() -> None:
    current_user = build_current_user()
    key = f"{current_user.company_id}/inspection/photo.jpg"

    with patch(
        "src.routes.inspections.inspections.get_inspection_photo",
        AsyncMock(side_effect=InspectionPhotoNotFound(key)),
    ):
        try:
            await inspections.get_inspection_photo(key, current_user)
        except HTTPException as error:
            assert error.status_code == 404
            assert error.detail == "Photo not found"
        else:
            raise AssertionError("Expected HTTPException")
