from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from starlette.datastructures import UploadFile

from src.models.auth.authentication import CurrentUser
from src.models.templates.domain import TemplateStructure
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
                    template_id=template_id,
                    structure=TemplateStructure(sections=[]),
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
            "Main Street 1",
            "2026-05-25",
            "Lekdetectie",
            "Zakelijk",
            [audio_file],
            current_user,
            extra_context="Extra",
            photo_files=[photo_file],
        )

    assert response.status == "processing"
    assert response.report_id
    store_files.assert_awaited_once()
    inspection_id = insert_inspection.await_args.args[0]
    assert insert_inspection.await_args.args[4:9] == (
        "Main Street 1",
        "Main Street 1",
        "Lekdetectie",
        "Zakelijk",
        "Extra",
    )
    insert_audio.assert_awaited_once_with(inspection_id, "/tmp/audio.m4a", "audio.m4a")
    insert_photo.assert_awaited_once_with(inspection_id, "/tmp/photo.jpg", "photo.jpg")
    insert_report.assert_awaited_once()
