from collections.abc import AsyncIterator
from io import BytesIO
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image

from src.main import app
from src.models.auth.authentication import CurrentUser
from src.routes import uploads
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
        company_name="Demo Company",
        email="admin@example.com",
        first_name="Admin",
        last_name="",
        role="admin",
    )


async def test_upload_logo_returns_blob_url(client: AsyncClient) -> None:
    current_user = build_admin_user()
    access_token = security.create_access_token(current_user)
    image = BytesIO()
    Image.new("RGB", (1, 1), color="red").save(image, format="PNG")
    image.seek(0)

    with (
        patch.object(
            auth_service.queries,
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
            files={"file": ("logo.png", image, "image/png")},
        )

    assert response.status_code == 200
    assert response.json() == {"url": "https://storage.example/logos/logo.png"}


async def test_upload_logo_rejects_unsupported_content_type() -> None:
    current_user = build_admin_user()

    response_file = uploads.UploadFile(filename="logo.gif", file=BytesIO(b"gif"))
    response_file.headers = {"content-type": "image/gif"}

    with pytest.raises(uploads.HTTPException) as error:
        await uploads.upload_logo(response_file, current_user)

    assert error.value.status_code == 422


async def test_upload_logo_rejects_large_file() -> None:
    current_user = build_admin_user()
    response_file = uploads.UploadFile(
        filename="logo.png",
        file=BytesIO(b"0" * 5_000_001),
        headers={"content-type": "image/png"},
    )

    with pytest.raises(uploads.HTTPException) as error:
        await uploads.upload_logo(response_file, current_user)

    assert error.value.status_code == 413
