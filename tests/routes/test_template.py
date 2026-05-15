from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src import main as main_module
from src.main import app
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import (
    TemplateConfigurationActive,
    TemplateConfigurationExtracting,
    TemplateConfigurationPendingReview,
    TemplateSection,
)
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


def create_frontend_build(tmp_path: Path) -> tuple[Path, Path]:
    frontend_dist_path = tmp_path / "dist"
    frontend_index_path = frontend_dist_path / "index.html"
    frontend_asset_path = frontend_dist_path / "assets" / "index-DP-JPQ9M.js"
    frontend_asset_path.parent.mkdir(parents=True)
    frontend_index_path.write_text("<!doctype html><html><body>fieldreport</body></html>")
    frontend_asset_path.write_text("console.log('fieldreport');")

    return frontend_dist_path, frontend_index_path


async def test_template_routes_require_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/template")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_get_template_returns_current_company_template_status(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.get_template_configuration",
            AsyncMock(
                return_value=TemplateConfigurationActive(
                    status="active",
                    reports_count=3,
                    sections=[TemplateSection(id="summary", label="Summary", type="text_block")],
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
        "reports_count": 3,
        "sections": [{"id": "summary", "label": "Summary", "type": "text_block", "fields": None}],
    }


async def test_post_template_analysis_accepts_repeated_files_field(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.start_template_analysis",
            AsyncMock(
                return_value=TemplateConfigurationExtracting(
                    status="extracting",
                    jobId="job-123",
                    reports_count=3,
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
    assert response.json() == {"status": "extracting", "jobId": "job-123", "reports_count": 3}
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
        auth_service.auth_repository,
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

    with (
        patch.object(
            auth_service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.get_template_analysis",
            AsyncMock(
                return_value=TemplateConfigurationPendingReview(
                    status="pending_review",
                    reports_count=3,
                    sections=[
                        TemplateSection(
                            id="findings",
                            label="Findings",
                            type="key_value_table",
                            fields=["Issue", "Action"],
                        )
                    ],
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
        "reports_count": 3,
        "sections": [
            {
                "id": "findings",
                "label": "Findings",
                "type": "key_value_table",
                "fields": ["Issue", "Action"],
            }
        ],
    }


async def test_get_template_analysis_returns_not_found_for_unknown_job(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_repository,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.template.templates.get_template_analysis",
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
            {"id": "summary", "label": "Executive Summary", "type": "text_block"},
            {
                "id": "findings",
                "label": "Findings",
                "type": "key_value_table",
                "fields": ["Issue", "Action"],
            },
        ]
    }

    with (
        patch.object(
            auth_service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.template.templates.confirm_template",
            AsyncMock(
                return_value=TemplateConfigurationActive(
                    status="active",
                    reports_count=3,
                    sections=[
                        TemplateSection(
                            id="summary",
                            label="Executive Summary",
                            type="text_block",
                        ),
                        TemplateSection(
                            id="findings",
                            label="Findings",
                            type="key_value_table",
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
        "reports_count": 3,
        "sections": [
            {
                "id": "summary",
                "label": "Executive Summary",
                "type": "text_block",
                "fields": None,
            },
            {
                "id": "findings",
                "label": "Findings",
                "type": "key_value_table",
                "fields": ["Issue", "Action"],
            },
        ],
    }


async def test_admin_template_path_returns_frontend_entrypoint(
    client: AsyncClient, tmp_path: Path
) -> None:
    frontend_dist_path, frontend_index_path = create_frontend_build(tmp_path)

    with (
        patch.object(main_module, "frontend_dist_path", frontend_dist_path),
        patch.object(main_module, "frontend_index_path", frontend_index_path),
    ):
        response = await client.get("/admin/template")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<!doctype html>" in response.text.lower()


async def test_api_like_frontend_path_returns_not_found(client: AsyncClient) -> None:
    response = await client.get("/api/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


async def test_frontend_static_asset_path_returns_asset_file(
    client: AsyncClient, tmp_path: Path
) -> None:
    frontend_dist_path, frontend_index_path = create_frontend_build(tmp_path)

    with (
        patch.object(main_module, "frontend_dist_path", frontend_dist_path),
        patch.object(main_module, "frontend_index_path", frontend_index_path),
    ):
        response = await client.get("/assets/index-DP-JPQ9M.js")

    assert response.status_code == 200
    assert "javascript" in response.headers["content-type"]


async def test_frontend_returns_not_found_when_frontend_build_is_missing() -> None:
    missing_index_path = Path("/tmp/fieldreport-missing-index.html")

    with patch.object(main_module, "frontend_index_path", missing_index_path):
        try:
            await main_module.frontend("admin/template")
        except HTTPException as error:
            response_status = error.status_code
            response_detail = error.detail
        else:
            raise AssertionError("Expected HTTPException")

    assert response_status == 404
    assert response_detail == "Not Found"
