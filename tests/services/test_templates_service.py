from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from starlette.datastructures import UploadFile

from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import StoredTemplateStructure, TemplateSection
from src.models.templates.pipeline import TemplateAnalysisFile, TemplateAnalysisJobStatus
from src.models.templates.records import TemplateAnalysisJobRecord
from src.models.templates.state import TemplateCompanyState
from src.services import templates as templates_service


def build_template_company_state(
    *,
    view_status: str = "not_configured",
    structure: StoredTemplateStructure | None = None,
    job_id: UUID | None = None,
    template_id: UUID | None = None,
    reports_count: int = 0,
    error_message: str | None = None,
) -> TemplateCompanyState:
    state_data = {
        "view_status": view_status,
        "job_id": job_id,
        "template_id": template_id,
        "reports_count": reports_count,
    }

    if structure is not None:
        state_data["structure"] = structure

    if error_message is not None:
        state_data["error_message"] = error_message

    return TemplateCompanyState.model_validate(state_data)


def build_analysis_job_record(
    *,
    job_id=None,
    company_id=None,
    template_id=None,
    status: TemplateAnalysisJobStatus | None = None,
    reports_count: int | None = None,
    structure: StoredTemplateStructure | None = None,
    error_message: str | None = None,
    created_at: datetime | None = None,
) -> TemplateAnalysisJobRecord:
    job_data = {
        "id": job_id if job_id is not None else uuid4(),
        "company_id": company_id if company_id is not None else uuid4(),
        "template_id": template_id,
        "status": status if status is not None else "queued",
        "reports_count": reports_count if reports_count is not None else 0,
        "created_at": created_at if created_at is not None else datetime.now(UTC),
    }

    if structure is not None:
        job_data["structure"] = structure

    if error_message is not None:
        job_data["error_message"] = error_message

    return TemplateAnalysisJobRecord.model_validate(job_data)


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


async def test_get_template_analysis_job_returns_active_job() -> None:
    current_user = build_current_user()
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="photos", label="Photos", render_type="photo_grid")]
    )

    with patch.object(
        templates_service.template_queries,
        "get_template_analysis_job",
        AsyncMock(
            return_value=build_analysis_job_record(
                status="active", reports_count=5, structure=structure
            )
        ),
    ):
        result = await templates_service.get_template_analysis_job(current_user, str(uuid4()))

    assert result.status == "active"
    assert result.reports_count == 5
    assert result.structure == structure


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
            templates_service.template_queries,
            "replace_template_analysis_job",
            AsyncMock(),
        ) as replace_job,
    ):
        result = await templates_service.start_template_analysis(current_user, files)

    assert result.status == "extracting"
    assert result.reports_count == 2
    store_files.assert_awaited_once_with(str(current_user.company_id), result.jobId, files)
    replace_job.assert_awaited_once_with(result.jobId, str(current_user.company_id), stored_files)


async def test_get_template_analysis_job_returns_pending_review_job() -> None:
    current_user = build_current_user()
    structure = StoredTemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )

    with patch.object(
        templates_service.template_queries,
        "get_template_analysis_job",
        AsyncMock(
            return_value=build_analysis_job_record(
                status="pending_review", reports_count=1, structure=structure
            )
        ),
    ):
        result = await templates_service.get_template_analysis_job(current_user, str(uuid4()))

    assert result.status == "pending_review"
    assert result.reports_count == 1
    assert result.structure == structure


async def test_get_template_analysis_job_raises_for_missing_job() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_queries,
        "get_template_analysis_job",
        AsyncMock(return_value=None),
    ):
        try:
            await templates_service.get_template_analysis_job(current_user, str(uuid4()))
        except LookupError:
            pass
        else:
            raise AssertionError("Expected LookupError")


async def test_confirm_template_creates_and_activates_template_from_reviewed_sections() -> None:
    current_user = build_current_user()
    job_id = uuid4()
    template_id = uuid4()
    sections = [
        TemplateSection(id="summary", label="Executive Summary", render_type="text_block"),
        TemplateSection(
            id="findings",
            label="Findings",
            render_type="key_value_table",
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
            templates_service,
            "load_template_company_state",
            AsyncMock(
                return_value=build_template_company_state(
                    view_status="pending_review",
                    job_id=job_id,
                    reports_count=3,
                )
            ),
        ),
        patch.object(
            templates_service.template_queries,
            "create_template",
            AsyncMock(),
        ) as create_template,
        patch.object(
            templates_service.template_queries,
            "set_active_template",
            AsyncMock(),
        ) as set_active_template,
        patch.object(
            templates_service.template_queries,
            "update_template_analysis_job",
            AsyncMock(),
        ) as update_job,
    ):
        result = await templates_service.confirm_template(current_user, sections)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 3,
        "sections": [
            {
                "id": "summary",
                "label": "Executive Summary",
                "order": 0,
                "render_type": "text_block",
                "found_in": 0,
            },
            {
                "id": "findings",
                "label": "Findings",
                "order": 0,
                "render_type": "key_value_table",
                "fields": ["Issue", "Action"],
                "found_in": 0,
            },
        ],
    }
    create_template.assert_awaited_once()
    set_active_template.assert_awaited_once_with(str(current_user.company_id), str(template_id))
    update_job.assert_awaited_once()


async def test_confirm_template_without_pending_job_returns_active_template() -> None:
    current_user = build_current_user()
    template_id = uuid4()
    sections = [TemplateSection(id="summary", label="Summary", render_type="text_block")]

    with (
        patch.object(templates_service, "uuid4", side_effect=[template_id]),
        patch.object(
            templates_service,
            "load_template_company_state",
            AsyncMock(return_value=build_template_company_state(view_status="not_configured")),
        ),
        patch.object(
            templates_service.template_queries,
            "create_template",
            AsyncMock(),
        ),
        patch.object(
            templates_service.template_queries,
            "set_active_template",
            AsyncMock(),
        ),
    ):
        result = await templates_service.confirm_template(current_user, sections)

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "reports_count": 0,
        "sections": [
            {
                "id": "summary",
                "label": "Summary",
                "order": 0,
                "render_type": "text_block",
                "found_in": 0,
            }
        ],
    }


async def test_update_pending_template_structure_updates_company_scoped_job() -> None:
    current_user = build_current_user()
    job_id = str(uuid4())
    sections = [TemplateSection(id="summary", label="Summary", render_type="text_block")]

    with patch.object(
        templates_service.template_queries,
        "update_pending_template_structure",
        AsyncMock(),
    ) as update_structure:
        await templates_service.update_pending_template_structure(current_user, job_id, sections)

    update_structure.assert_awaited_once_with(
        job_id,
        str(current_user.company_id),
        StoredTemplateStructure(
            sections=[
                TemplateSection(id="summary", label="Summary", render_type="text_block")
            ]
        ),
    )
