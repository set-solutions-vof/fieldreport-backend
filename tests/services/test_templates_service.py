from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from starlette.datastructures import UploadFile

from src.models.auth.authentication import CurrentUser
from src.models.templates.template import TemplateSection
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


def test_map_sections_returns_empty_list_for_missing_structure() -> None:
    assert templates_service.map_sections(None) == []


async def test_get_template_configuration_returns_not_configured() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(return_value=({"active_template_id": None, "active_structure": None}, None)),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump() == {"status": "not_configured"}


async def test_get_template_configuration_returns_extracting_job_state() -> None:
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
                    "status": "extracting",
                    "reports_count": 3,
                    "structure": None,
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


async def test_get_template_configuration_returns_pending_review_job_state() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(
            return_value=(
                {"active_template_id": None, "active_structure": None},
                {
                    "id": uuid4(),
                    "status": "pending_review",
                    "reports_count": 2,
                    "structure": templates_service.build_structure(
                        [TemplateSection(id="summary", label="Summary", type="text")]
                    ),
                },
            )
        ),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "reports_count": 2,
        "sections": [{"id": "summary", "label": "Summary", "type": "text"}],
    }


async def test_get_template_configuration_returns_active_job_state() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_company_template_context",
        AsyncMock(
            return_value=(
                {"active_template_id": None, "active_structure": None},
                {
                    "id": uuid4(),
                    "status": "active",
                    "reports_count": 4,
                    "structure": templates_service.build_structure(
                        [TemplateSection(id="photos", label="Photos", type="photo")]
                    ),
                },
            )
        ),
    ):
        result = await templates_service.get_template_configuration(current_user)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 4,
        "sections": [{"id": "photos", "label": "Photos", "type": "photo"}],
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
                    "active_structure": templates_service.build_structure(
                        [
                            TemplateSection(
                                id="findings",
                                label="Findings",
                                type="kv",
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
            {"id": "findings", "label": "Findings", "type": "kv", "fields": ["Issue", "Action"]}
        ],
    }


async def test_start_template_analysis_replaces_existing_company_job() -> None:
    current_user = build_current_user()
    files = [
        build_upload_file("one.pdf"),
        build_upload_file("two.pdf"),
        build_upload_file("three.pdf"),
    ]

    with patch.object(
        templates_service.template_repository,
        "replace_template_analysis_job",
        AsyncMock(),
    ) as replace_job:
        result = await templates_service.start_template_analysis(current_user, files)

    assert result.status == "extracting"
    assert result.reports_count == 3
    assert len(result.jobId) > 0
    replace_job.assert_awaited_once_with(result.jobId, str(current_user.company_id), 3)


async def test_get_template_analysis_promotes_extracting_job_to_pending_review() -> None:
    current_user = build_current_user()
    job_id = str(uuid4())
    job_row = {
        "id": uuid4(),
        "status": "extracting",
        "reports_count": 3,
        "structure": None,
    }

    with (
        patch.object(
            templates_service.template_repository,
            "get_template_analysis_job",
            AsyncMock(return_value=job_row),
        ),
        patch.object(
            templates_service.template_repository,
            "update_template_analysis_job",
            AsyncMock(),
        ) as update_job,
    ):
        result = await templates_service.get_template_analysis(current_user, job_id)

    assert result.status == "pending_review"
    assert result.reports_count == 3
    assert [section.type for section in result.sections] == ["text", "kv", "measure", "photo"]
    update_job.assert_awaited_once()


async def test_get_template_analysis_raises_for_missing_job() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_repository,
        "get_template_analysis_job",
        AsyncMock(return_value=None),
    ):
        try:
            await templates_service.get_template_analysis(current_user, str(uuid4()))
        except templates_service.TemplateAnalysisNotFoundError:
            pass
        else:
            raise AssertionError("Expected TemplateAnalysisNotFoundError")


async def test_get_template_analysis_returns_pending_review_job() -> None:
    current_user = build_current_user()
    structure = templates_service.build_structure(
        [TemplateSection(id="summary", label="Summary", type="text")]
    )

    with patch.object(
        templates_service.template_repository,
        "get_template_analysis_job",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "status": "pending_review",
                "reports_count": 1,
                "structure": structure,
            }
        ),
    ):
        result = await templates_service.get_template_analysis(current_user, str(uuid4()))

    assert result.model_dump(exclude_none=True) == {
        "status": "pending_review",
        "reports_count": 1,
        "sections": [{"id": "summary", "label": "Summary", "type": "text"}],
    }


async def test_get_template_analysis_returns_active_job() -> None:
    current_user = build_current_user()
    structure = templates_service.build_structure(
        [TemplateSection(id="photos", label="Photos", type="photo")]
    )

    with patch.object(
        templates_service.template_repository,
        "get_template_analysis_job",
        AsyncMock(
            return_value={
                "id": uuid4(),
                "status": "active",
                "reports_count": 5,
                "structure": structure,
            }
        ),
    ):
        result = await templates_service.get_template_analysis(current_user, str(uuid4()))

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 5,
        "sections": [{"id": "photos", "label": "Photos", "type": "photo"}],
    }


async def test_confirm_template_creates_and_activates_template_from_reviewed_sections() -> None:
    current_user = build_current_user()
    job_id = uuid4()
    template_id = uuid4()
    sections = [
        TemplateSection(id="summary", label="Executive Summary", type="text"),
        TemplateSection(id="findings", label="Findings", type="kv", fields=["Issue", "Action"]),
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
            {"id": "summary", "label": "Executive Summary", "type": "text"},
            {"id": "findings", "label": "Findings", "type": "kv", "fields": ["Issue", "Action"]},
        ],
    }
    create_template.assert_awaited_once()
    set_active_template.assert_awaited_once_with(str(current_user.company_id), str(template_id))
    update_job.assert_awaited_once()


async def test_confirm_template_without_pending_job_returns_active_template() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    sections = [TemplateSection(id="summary", label="Summary", type="text")]

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
        "sections": [{"id": "summary", "label": "Summary", "type": "text"}],
    }
