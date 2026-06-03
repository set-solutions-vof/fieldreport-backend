from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from starlette.datastructures import UploadFile

from src.exceptions import TemplateAnalysisJobNotFound
from src.models.auth.authentication import CurrentUser
from src.models.enums.template_analysis_job_status import TemplateAnalysisJobStatus
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import TemplateAnalysisJobRecord
from src.services import templates as templates_service


def build_analysis_job_record(
    *,
    job_id=None,
    company_id=None,
    status: TemplateAnalysisJobStatus | None = None,
    source_reports_count: int | None = None,
    structure: TemplateStructure | None = None,
    failure_message: str | None = None,
    created_at: datetime | None = None,
) -> TemplateAnalysisJobRecord:
    job_data = {
        "id": job_id if job_id is not None else uuid4(),
        "company_id": company_id if company_id is not None else uuid4(),
        "status": status if status is not None else "queued",
        "source_reports_count": source_reports_count if source_reports_count is not None else 0,
        "structure": structure if structure is not None else TemplateStructure(sections=[]),
        "created_at": created_at if created_at is not None else datetime.now(UTC),
    }

    if failure_message is not None:
        job_data["failure_message"] = failure_message

    return TemplateAnalysisJobRecord.model_validate(job_data)


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="demo@fieldreport.local",
        name="Demo User",
        role="admin",
    )


def build_upload_file(name: str) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(b"%PDF-1.4"))


async def test_get_template_analysis_job_returns_active_job() -> None:
    current_user = build_current_user()
    structure = TemplateStructure(
        sections=[TemplateSection(id="photos", label="Photos", render_type="photo_grid")]
    )

    with patch.object(
        templates_service.template_queries,
        "get_template_analysis_job",
        AsyncMock(
            return_value=build_analysis_job_record(
                status="active", source_reports_count=5, structure=structure
            )
        ),
    ):
        result = await templates_service.get_template_analysis_job(current_user, str(uuid4()))

    assert result.status == "active"
    assert result.source_reports_count == 5
    assert result.structure == structure


async def test_start_template_analysis_stores_files_and_creates_job() -> None:
    current_user = build_current_user()
    files = [
        build_upload_file("one.pdf"),
        build_upload_file("two.pdf"),
    ]
    with (
        patch.object(
            templates_service.blob,
            "upload_form_file",
            AsyncMock(return_value="https://storage.example/blob"),
        ) as upload_file,
        patch.object(
            templates_service.template_queries,
            "replace_template_analysis_job",
            AsyncMock(),
        ) as replace_job,
    ):
        result = await templates_service.start_template_analysis(current_user, files)

    assert result.status == "processing"
    assert result.source_reports_count == 2
    assert upload_file.await_count == 2
    replace_job.assert_awaited_once()
    stored_files = replace_job.await_args.args[2]
    assert [file.original_file_name for file in stored_files] == ["one.pdf", "two.pdf"]


async def test_get_template_analysis_job_returns_pending_review_job() -> None:
    current_user = build_current_user()
    structure = TemplateStructure(
        sections=[TemplateSection(id="summary", label="Summary", render_type="text_block")]
    )

    with patch.object(
        templates_service.template_queries,
        "get_template_analysis_job",
        AsyncMock(
            return_value=build_analysis_job_record(
                status="pending_review", source_reports_count=1, structure=structure
            )
        ),
    ):
        result = await templates_service.get_template_analysis_job(current_user, str(uuid4()))

    assert result.status == "pending_review"
    assert result.source_reports_count == 1
    assert result.structure == structure


async def test_get_template_analysis_job_raises_for_missing_job() -> None:
    current_user = build_current_user()

    with patch.object(
        templates_service.template_queries,
        "get_template_analysis_job",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(TemplateAnalysisJobNotFound):
            await templates_service.get_template_analysis_job(current_user, str(uuid4()))


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
    job = build_analysis_job_record(job_id=job_id, status="pending_review", source_reports_count=3)

    with (
        patch.object(templates_service, "uuid4", side_effect=[template_id]),
        patch.object(
            templates_service.template_queries,
            "fetch_latest_template_analysis_job",
            AsyncMock(return_value=job),
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
            "delete_template_analysis_job",
            AsyncMock(),
        ) as delete_job,
    ):
        result = await templates_service.confirm_template(
            current_user, TemplateStructure(sections=sections)
        )

    assert result.model_dump(exclude_none=True) == {
        "status": "active",
        "source_reports_count": 3,
        "metadata_fields": [],
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
    delete_job.assert_awaited_once_with(str(job_id), str(current_user.company_id))
