from collections.abc import AsyncIterator
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.auth.authentication import CurrentUser
from src.security import authentication as security
from src.services import authentication as auth_service


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client


def build_admin_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="admin@lekk.nl",
        name="Admin",
        role="admin",
    )


async def test_upload_logo_returns_blob_url(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)

    with (
        patch.object(
            auth_service.auth_queries,
            "get_user_by_id",
            AsyncMock(return_value=current_user),
        ),
        patch(
            "src.routes.uploads.blob.upload_file",
            AsyncMock(return_value="https://storage.example/logos/logo.png"),
        ),
    ):
        response = await client.post(
            "/api/v1/uploads/logo",
            headers={"Authorization": f"Bearer {access_token}"},
            files={"file": ("logo.png", BytesIO(b"png"), "image/png")},
        )

    assert response.status_code == 200
    assert response.json() == {"url": "https://storage.example/logos/logo.png"}
