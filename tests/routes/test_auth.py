from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import bcrypt
import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.auth.authentication import AuthenticatedUser, CurrentUser
from src.models.reports.report import (
    ReportDetail,
    ReportSection,
    ReportSectionSource,
    ReportSummary,
)
from src.security import authentication as security
from src.services import authentication as service
from src.services import reports


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


def build_authenticated_user() -> AuthenticatedUser:
    password_hash = bcrypt.hashpw(b"LekkDemo2026!", bcrypt.gensalt()).decode()

    return AuthenticatedUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="sanne.devries@lekk.nl",
        password_hash=password_hash,
        name="Sanne de Vries",
        role="admin",
    )


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="LEKK BV",
        email="jeroen.vandijk@lekk.nl",
        name="Jeroen van Dijk",
        role="inspector",
    )


def build_report_summary(company_id: UUID) -> ReportSummary:
    return ReportSummary(
        id=uuid4(),
        company_id=company_id,
        status="draft",
        client_name="ACME",
        address="Main Street 1",
        inspection_date=datetime(2026, 5, 8, 12, 30, tzinfo=UTC),
        inspector_name="Jeroen van Dijk",
    )


async def test_login_json_returns_tokens_for_valid_credentials(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login/json",
            json={"email": authenticated_user.email, "password": "LekkDemo2026!"},
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


async def test_login_form_returns_tokens_for_valid_credentials(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": authenticated_user.email, "password": "LekkDemo2026!"},
        )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


async def test_login_returns_unauthorized_for_wrong_password(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login/json",
            json={"email": authenticated_user.email, "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_login_form_returns_unauthorized_for_wrong_password(client: AsyncClient) -> None:
    authenticated_user = build_authenticated_user()

    with patch.object(
        service.auth_repository, "get_user_by_email", AsyncMock(return_value=authenticated_user)
    ):
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": authenticated_user.email, "password": "wrong-password"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_refresh_returns_new_access_token(client: AsyncClient) -> None:
    current_user = build_current_user()
    refresh_token = security.create_refresh_token(current_user)

    with patch.object(
        service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
    ):
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()


async def test_refresh_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


async def test_me_requires_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_me_returns_authenticated_user(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(
        service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
    ):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "company_id": str(current_user.company_id),
        "company_name": current_user.company_name,
    }


async def test_reports_require_access_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/reports")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


async def test_reports_accept_access_token(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    fake_report = build_report_summary(current_user.company_id)

    with (
        patch.object(
            service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.reports.reports.list_reports_for_user",
            AsyncMock(return_value=[fake_report]),
        ),
    ):
        response = await client.get(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(fake_report.id),
            "company_id": str(current_user.company_id),
            "status": "draft",
            "client_name": "ACME",
            "address": "Main Street 1",
            "inspection_date": "2026-05-08T12:30:00+00:00",
            "inspector_name": "Jeroen van Dijk",
        }
    ]


async def test_report_detail_accepts_access_token(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)
    report_id = uuid4()
    capture_time = datetime(2026, 5, 8, 12, 45, tzinfo=UTC)
    fake_report = ReportDetail(
        id=report_id,
        status="draft",
        client_name="ACME",
        address="Main Street 1",
        inspection_date=datetime(2026, 5, 8, 12, 30, tzinfo=UTC),
        inspector_name="Jeroen van Dijk",
        sections=[
            ReportSection(
                id=uuid4(),
                section_key="technische_bevindingen",
                ai_draft="Draft",
                field_expert_content=None,
                is_approved=False,
                sources=[
                    ReportSectionSource(
                        type="image",
                        timestamp_start=None,
                        timestamp_end=None,
                        capture_time=capture_time,
                        content_summary="Image summary",
                    )
                ],
            )
        ],
    )

    with (
        patch.object(
            service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.reports.reports.get_report_detail",
            AsyncMock(return_value=fake_report),
        ),
    ):
        response = await client.get(
            f"/api/v1/reports/{report_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "id": str(report_id),
        "status": "draft",
        "client_name": "ACME",
        "address": "Main Street 1",
        "inspection_date": "2026-05-08T12:30:00+00:00",
        "inspector_name": "Jeroen van Dijk",
        "sections": [
            {
                "id": str(fake_report.sections[0].id),
                "section_key": "technische_bevindingen",
                "label": "Technische Bevindingen",
                "ai_draft": "Draft",
                "field_expert_content": None,
                "is_approved": False,
                "sources": [
                    {
                        "type": "image",
                        "timestamp_start": None,
                        "timestamp_end": None,
                        "capture_time": "2026-05-08T12:45:00+00:00",
                        "content_summary": "Image summary",
                    }
                ],
            }
        ],
    }


async def test_report_detail_returns_not_found(client: AsyncClient) -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)
    report_id = uuid4()

    with (
        patch.object(
            service.auth_repository, "get_user_by_id", AsyncMock(return_value=current_user)
        ),
        patch(
            "src.routes.reports.reports.get_report_detail",
            AsyncMock(side_effect=reports.ReportNotFoundError),
        ),
    ):
        response = await client.get(
            f"/api/v1/reports/{report_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found"}
