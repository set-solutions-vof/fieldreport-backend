from collections.abc import AsyncIterator
from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateStatusActive,
    TemplateStatusProcessing,
)
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.models.templates.records import TemplateAnalysisJobRecord
from src.routes import template as template_route
from src.security import authentication as security
from src.services import authentication as auth_service


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="jeroen.vandijk@lekk.nl",
        name="Jeroen van Dijk",
        role="admin",
    )


async def test_template_routes_require_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/template")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_get_template_returns_current_company_template_status(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_queries, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.load_template_configuration",
            AsyncMock(
                return_value=TemplateStatusActive(
                    status="active",
                    sections=[
                        TemplateSection(id="summary", label="Summary", render_type="text_block")
                    ],
                    source_reports_count=3,
                )
            ),
        ),
    ):
        response = await client.get(
            "/api/v1/template",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "active",
        "source_reports_count": 3,
        "sections": [
            {
                "id": "summary",
                "label": "Summary",
                "order": 0,
                "render_type": "text_block",
                "fields": None,
                "found_in": 0,
                "groups": None,
            }
        ],
    }


async def test_post_template_analysis_accepts_repeated_files_field(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_queries, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.start_template_analysis",
            AsyncMock(
                return_value=TemplateStatusProcessing(
                    status="processing",
                    job_id="job-123",
                    source_reports_count=3,
                )
            ),
        ) as start_analysis,
    ):
        response = await client.post(
            "/api/v1/template/analysis",
            headers={"Authorization": f"Bearer {access_token}"},
            files=[
                ("files", ("one.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")),
                ("files", ("two.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")),
                ("files", ("three.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")),
            ],
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "processing",
        "job_id": "job-123",
        "source_reports_count": 3,
    }
    start_analysis.assert_awaited_once()
    assert len(start_analysis.await_args.args[1]) == 3


async def test_post_template_analysis_rejects_empty_upload_list(client: AsyncClient) -> None:
    current_user = build_current_user()

    try:
        await template_route.start_template_analysis([], current_user)
    except HTTPException as error:
        response_status = error.status_code
        response_detail = error.detail
    else:
        raise AssertionError("Expected HTTPException")

    assert response_status == 400
    assert response_detail == "At least one file is required"


async def test_post_template_analysis_missing_files_returns_validation_error(
    client: AsyncClient,
) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        auth_service.auth_queries,
        "get_user_by_id",
        AsyncMock(return_value=current_user),
    ):
        response = await client.post(
            "/api/v1/template/analysis",
            headers={"Authorization": f"Bearer {access_token}"},
            files=[],
        )

    assert response.status_code == 422


async def test_get_template_analysis_returns_pending_review(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)
    job_id = uuid4()

    with (
        patch.object(
            auth_service.auth_queries, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.get_template_analysis_job",
            AsyncMock(
                return_value=TemplateAnalysisJobRecord(
                    id=job_id,
                    company_id=current_user.company_id,
                    status="pending_review",
                    source_reports_count=3,
                    created_at=datetime.now(UTC),
                    structure=TemplateStructure(
                        sections=[
                            TemplateSection(
                                id="findings",
                                label="Findings",
                                render_type="key_value_table",
                                fields=["Issue", "Action"],
                            )
                        ]
                    ),
                )
            ),
        ),
    ):
        response = await client.get(
            "/api/v1/template/analysis/job-123",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "pending_review",
        "job_id": str(job_id),
        "source_reports_count": 3,
        "sections": [
            {
                "id": "findings",
                "label": "Findings",
                "order": 0,
                "render_type": "key_value_table",
                "fields": ["Issue", "Action"],
                "found_in": 0,
                "groups": None,
            }
        ],
    }


async def test_get_template_analysis_returns_not_found_for_unknown_job(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.template.templates.get_template_analysis_job",
            AsyncMock(side_effect=LookupError),
        ),
    ):
        response = await client.get(
            "/api/v1/template/analysis/job-123",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Template analysis not found"}


async def test_confirm_template_returns_active_template(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)
    request_body = {
        "sections": [
            {"id": "summary", "label": "Executive Summary", "render_type": "text_block"},
            {
                "id": "findings",
                "label": "Findings",
                "render_type": "key_value_table",
                "fields": ["Issue", "Action"],
            },
        ]
    }

    with (
        patch.object(
            auth_service.auth_queries, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.confirm_template",
            AsyncMock(
                return_value=TemplateStatusActive(
                    status="active",
                    source_reports_count=3,
                    sections=[
                        TemplateSection(
                            id="summary",
                            label="Executive Summary",
                            render_type="text_block",
                        ),
                        TemplateSection(
                            id="findings",
                            label="Findings",
                            render_type="key_value_table",
                            fields=["Issue", "Action"],
                        ),
                    ],
                )
            ),
        ),
    ):
        response = await client.post(
            "/api/v1/template",
            headers={"Authorization": f"Bearer {access_token}"},
            json=request_body,
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "active",
        "source_reports_count": 3,
        "sections": [
            {
                "id": "summary",
                "label": "Executive Summary",
                "order": 0,
                "render_type": "text_block",
                "fields": None,
                "found_in": 0,
                "groups": None,
            },
            {
                "id": "findings",
                "label": "Findings",
                "order": 0,
                "render_type": "key_value_table",
                "fields": ["Issue", "Action"],
                "found_in": 0,
                "groups": None,
            },
        ],
    }
