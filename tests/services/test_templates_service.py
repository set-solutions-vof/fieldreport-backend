from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from starlette.datastructures import UploadFile

from src.db.template_mapper import build_structure
from src.models.auth.authentication import CurrentUser
from src.models.templates.template import TemplateSection
from src.models.templates.template_analysis import TemplateAnalysisFile
from src.services import templates as templates_service


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="demo@fieldreport.local",
        name="Demo User",
        role="admin",
    )


def build_upload_file(name: str) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(b"%PDF-1.4"))


async def test_get_template_configuration_returns_not_configured() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(return_value=({"active_template_id": None, "active_structure": None}, None)),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump() == {"status": "not_configured"}


async def test_get_template_configuration_maps_queued_job_to_extracting() -> None:
    current_user = build_current_user()
    job_id = uuid4()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(
            return_value=(
                {"active_template_id": None, "active_structure": None},
                {
                    "id": job_id,
                    "status": "queued",
                    "reports_count": 3,
                    "structure": None,
                    "error_message": None,
                },
            )
        ),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump() == {
        "status": "extracting",
        "jobId": str(job_id),
        "reports_count": 3,
    }


async def test_get_template_configuration_returns_failed_job_state() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(
            return_value=(
                {"active_template_id": None, "active_structure": None},
                {
                    "id": uuid4(),
                    "status": "failed",
                    "reports_count": 2,
                    "structure": None,
                    "error_message": "model error",
                },
            )
        ),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump() == {
        "status": "failed",
        "reports_count": 2,
        "error_message": "model error",
    }


async def test_get_template_configuration_returns_active_company_template() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(
            return_value=(
                {
                    "active_template_id": uuid4(),
                    "active_structure": build_structure(
                        [
                            TemplateSection(
                                id="findings",
                                label="Findings",
                                type="key_value_table",
                                fields=["Issue", "Action"],
                            )
                        ]
                    ),
                },
                None,
            )
        ),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 0,
        "sections": [
            {
                "id": "findings",
                "label": "Findings",
                "type": "key_value_table",
                "fields": ["Issue", "Action"],
            }
        ],
    }


async def test_get_template_analysis_returns_active_job() -> None:
    current_user = build_current_user()
    structure = build_structure([TemplateSection(id="photos", label="Photos", type="photo_grid")])

    with patch.object(
        templates_service.template_repository,
        "get_template_analysis_job",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "status": "active",
                "reports_count": 5,
                "structure": structure,
                "error_message": None,
            }
        ),
    ):
        result = await templates_service.get_template_analysis(current_user, str(uuid4()))

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 5,
        "sections": [{"id": "photos", "label": "Photos", "type": "photo_grid"}],
    }


async def test_start_template_analysis_stores_files_and_creates_job() -> None:
    current_user = build_current_user()
    files = [
        build_upload_file("one.pdf"),
        build_upload_file("two.pdf"),
    ]
    stored_files = [
        TemplateAnalysisFile(file_name="one.pdf", storage_path="/tmp/one.pdf"),
        TemplateAnalysisFile(file_name="two.pdf", storage_path="/tmp/two.pdf"),
    ]

    with (
        patch.object(
            templates_service.template_file_storage,
            "store_template_analysis_files",
            AsyncMock(return_value=stored_files),
        ) as store_files,
        patch.object(
            templates_service.template_repository,
            "replace_template_analysis_job",
            AsyncMock(),
        ) as replace_job,
    ):
        result = await templates_service.start_template_analysis(current_user, files)

    assert result.status == "extracting"
    assert result.reports_count == 2
    store_files.assert_awaited_once_with(str(current_user.company_id), result.jobId, files)
    replace_job.assert_awaited_once_with(result.jobId, str(current_user.company_id), stored_files)


async def test_get_template_analysis_returns_pending_review_job() -> None:
    current_user = build_current_user()
    structure = build_structure([TemplateSection(id="summary", label="Summary", type="text_block")])

    with patch.object(
        templates_service.template_repository,
        "get_template_analysis_job",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "status": "pending_review",
                "reports_count": 1,
                "structure": structure,
                "error_message": None,
            }
        ),
    ):
        result = await templates_service.get_template_analysis(current_user, str(uuid4()))

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "reports_count": 1,
        "sections": [{"id": "summary", "label": "Summary", "type": "text_block"}],
    }


async def test_get_template_analysis_raises_for_missing_job() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_template_analysis_job",
        AsyncMock(return_value=None),
    ):
        try:
            await templates_service.get_template_analysis(current_user, str(uuid4()))
        except LookupError:
            pass
        else:
            raise AssertionError("Expected LookupError")


async def test_confirm_template_creates_and_activates_template_from_reviewed_sections() -> None:
    current_user = build_current_user()
    job_id = uuid4()
    template_id = uuid4()
    sections = [
        TemplateSection(id="summary", label="Executive Summary", type="text_block"),
        TemplateSection(
            id="findings",
            label="Findings",
            type="key_value_table",
            fields=["Issue", "Action"],
        ),
    ]

    with (
        patch.object(
            templates_service,
            "uuid4",
            side_effect=[template_id],
        ),
        patch.object(
            templates_service.template_repository,
            "get_company_template_context",
            AsyncMock(
                return_value=(
                    {"active_template_id": None, "active_structure": None},
                    {
                        "id": job_id,
                        "status": "pending_review",
                        "reports_count": 3,
                        "structure": None,
                        "error_message": None,
                    },
                )
            ),
        ),
        patch.object(
            templates_service.template_repository,
            "create_template",
            AsyncMock(),
        ) as create_template,
        patch.object(
            templates_service.template_repository,
            "set_active_template",
            AsyncMock(),
        ) as set_active_template,
        patch.object(
            templates_service.template_repository,
            "update_template_analysis_job",
            AsyncMock(),
        ) as update_job,
    ):
        result = await templates_service.confirm_template(current_user, sections)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 3,
        "sections": [
            {"id": "summary", "label": "Executive Summary", "type": "text_block"},
            {
                "id": "findings",
                "label": "Findings",
                "type": "key_value_table",
                "fields": ["Issue", "Action"],
            },
        ],
    }
    create_template.assert_awaited_once()
    set_active_template.assert_awaited_once_with(str(current_user.company_id), str(template_id))
    update_job.assert_awaited_once()


async def test_confirm_template_without_pending_job_returns_active_template() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    sections = [TemplateSection(id="summary", label="Summary", type="text_block")]

    with (
        patch.object(templates_service, "uuid4", side_effect=[template_id]),
        patch.object(
            templates_service.template_repository,
            "get_company_template_context",
            AsyncMock(
                return_value=(
                    {"active_template_id": uuid4(), "active_structure": None},
                    None,
                )
            ),
        ),
        patch.object(
            templates_service.template_repository,
            "create_template",
            AsyncMock(),
        ),
        patch.object(
            templates_service.template_repository,
            "set_active_template",
            AsyncMock(),
        ),
    ):
        result = await templates_service.confirm_template(current_user, sections)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 0,
        "sections": [{"id": "summary", "label": "Summary", "type": "text_block"}],
    }
