from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.auth.authentication import CurrentUser
from src.models.templates.configuration import TemplateStatusActive
from src.models.templates.domain import TemplateSection, TemplateStructure
from src.security import authentication as security
from src.services import authentication as auth_service

FIXED_TEMPLATE_UPDATED_AT = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)
FIXED_TEMPLATE_ID = "11111111-1111-4111-8111-111111111111"


def build_active_template_status(**overrides) -> TemplateStatusActive:
    payload = {
        "status": "active",
        "metadata_fields": [],
        "sections": [TemplateSection(id="summary", label="Summary", render_type="text_block")],
        "source_reports_count": 3,
        "template_id": FIXED_TEMPLATE_ID,
        "version": 2,
        "updated_at": FIXED_TEMPLATE_UPDATED_AT,
    }
    payload.update(overrides)
    return TemplateStatusActive(**payload)


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def build_current_user(*, role: str = "admin") -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector.user@example.com",
        first_name="Inspector",
        last_name="User",
        role=role,
    )


async def test_template_routes_require_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/template")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_get_template_returns_current_company_template_status(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch(
            "src.routes.template.templates.load_template_configuration",
            AsyncMock(
                return_value=build_active_template_status(),
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
        "metadata_fields": [],
        "template_id": FIXED_TEMPLATE_ID,
        "version": 2,
        "updated_at": FIXED_TEMPLATE_UPDATED_AT.isoformat().replace("+00:00", "Z"),
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


async def test_get_template_allows_inspector(client: AsyncClient) -> None:
    current_user = build_current_user(role="inspector")
    access_token = security.create_access_token(current_user)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch(
            "src.routes.template.templates.load_template_configuration",
            AsyncMock(
                return_value=build_active_template_status(
                    sections=[],
                    source_reports_count=1,
                ),
            ),
        ),
    ):
        response = await client.get(
            "/api/v1/template",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200


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
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch(
            "src.routes.template.templates.confirm_template",
            AsyncMock(
                return_value=build_active_template_status(
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

    assert response.status_code == 201
    assert response.json() == {
        "status": "active",
        "source_reports_count": 3,
        "metadata_fields": [],
        "template_id": FIXED_TEMPLATE_ID,
        "version": 2,
        "updated_at": FIXED_TEMPLATE_UPDATED_AT.isoformat().replace("+00:00", "Z"),
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


async def test_confirm_template_returns_unprocessable_when_confirmation_not_allowed(
    client: AsyncClient,
) -> None:
    from src.exceptions import TemplateConfirmationNotAllowed

    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch(
            "src.routes.template.templates.confirm_template",
            AsyncMock(side_effect=TemplateConfirmationNotAllowed()),
        ),
    ):
        response = await client.post(
            "/api/v1/template",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"sections": []},
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Template cannot be confirmed"}


async def test_get_template_preview_pdf_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/template/preview-pdf")

    assert response.status_code == 401


async def test_get_template_preview_pdf_returns_pdf_when_key_exists(client: AsyncClient) -> None:
    from tests.db.sqlalchemy_fakes import build_connection

    current_user = build_current_user()
    access_token = security.create_access_token(current_user)
    pdf_bytes = b"%%PDF fake"

    connection = build_connection(row={"preview_pdf_storage_key": "thermofly/paneel/abc_preview.pdf"})
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch("src.routes.template.get_database", return_value=pool),
        patch(
            "src.routes.template.download_file",
            AsyncMock(return_value=(pdf_bytes, "application/pdf")),
        ),
    ):
        response = await client.get(
            "/api/v1/template/preview-pdf",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.content == pdf_bytes
    assert "application/pdf" in response.headers["content-type"]


async def test_get_template_preview_pdf_returns_404_when_key_is_null(client: AsyncClient) -> None:
    from tests.db.sqlalchemy_fakes import build_connection

    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    connection = build_connection(row={"preview_pdf_storage_key": None})
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch("src.routes.template.get_database", return_value=pool),
    ):
        response = await client.get(
            "/api/v1/template/preview-pdf",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Template preview not found"}


async def test_get_template_preview_pdf_returns_pdf_via_query_param_token(client: AsyncClient) -> None:
    from tests.db.sqlalchemy_fakes import build_connection

    current_user = build_current_user()
    access_token = security.create_access_token(current_user)
    pdf_bytes = b"%%PDF fake"

    connection = build_connection(row={"preview_pdf_storage_key": "thermofly/paneel/abc_preview.pdf"})
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch("src.routes.template.get_database", return_value=pool),
        patch(
            "src.routes.template.download_file",
            AsyncMock(return_value=(pdf_bytes, "application/pdf")),
        ),
    ):
        response = await client.get(f"/api/v1/template/preview-pdf?access_token={access_token}")

    assert response.status_code == 200
    assert response.content == pdf_bytes


async def test_get_template_preview_pdf_returns_401_when_token_is_invalid(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/template/preview-pdf",
        headers={"Authorization": "Bearer not.a.valid.token"},
    )

    assert response.status_code == 401


async def test_get_template_preview_pdf_returns_401_when_token_type_is_refresh(client: AsyncClient) -> None:
    current_user = build_current_user()
    refresh_token = security.create_refresh_token(current_user)

    response = await client.get(
        "/api/v1/template/preview-pdf",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401


async def test_get_template_preview_pdf_returns_401_when_user_not_found(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=None)):
        response = await client.get(
            "/api/v1/template/preview-pdf",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 401


async def test_get_template_preview_pdf_returns_404_when_no_template(client: AsyncClient) -> None:
    from tests.db.sqlalchemy_fakes import build_connection

    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    connection = build_connection(row=None)
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch.object(auth_service.queries, "get_user_by_id", AsyncMock(return_value=current_user)),
        patch("src.routes.template.get_database", return_value=pool),
    ):
        response = await client.get(
            "/api/v1/template/preview-pdf",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
