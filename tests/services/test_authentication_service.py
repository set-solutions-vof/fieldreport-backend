from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import AuthenticationFailed
from src.models.auth.authentication import LoginCredentials, TokenClaims
from src.services import authentication as service


async def test_refresh_raises_for_access_token_claims() -> None:
    claims = TokenClaims(sub=uuid4(), company_id=uuid4(), role="admin", exp=1, type="access")

    with patch.object(service.authentication, "decode_token", return_value=claims):
        with pytest.raises(AuthenticationFailed):
            await service.refresh("token")


async def test_refresh_raises_when_repository_returns_none() -> None:
    claims = TokenClaims(sub=uuid4(), company_id=None, role=None, exp=1, type="refresh")

    with (
        patch.object(service.authentication, "decode_token", return_value=claims),
        patch.object(service.queries, "get_user_by_id", AsyncMock(return_value=None)),
    ):
        with pytest.raises(AuthenticationFailed):
            await service.refresh("token")


async def test_login_checks_dummy_hash_when_email_is_missing() -> None:
    with (
        patch.object(service.queries, "get_user_by_email", AsyncMock(return_value=None)),
        patch.object(service.bcrypt, "hashpw", return_value=b"dummy-hash") as hash_password,
        patch.object(service.bcrypt, "checkpw", return_value=False) as check_password,
    ):
        with pytest.raises(AuthenticationFailed):
            await service.login(LoginCredentials(email="missing@example.com", password="secret"))

    hash_password.assert_called_once()
    check_password.assert_called_once_with(b"secret", b"dummy-hash")


async def test_login_records_last_sign_in_at() -> None:
    from tests.routes.test_auth import build_authenticated_user

    authenticated_user = build_authenticated_user()

    with (
        patch.object(
            service.queries,
            "get_user_by_email",
            AsyncMock(return_value=authenticated_user),
        ),
        patch.object(
            service.queries,
            "update_last_sign_in_at",
            AsyncMock(),
        ) as update_last_sign_in_at,
        patch.object(service.authentication, "verify_password", return_value=True),
        patch.object(service.authentication, "create_access_token", return_value="access"),
        patch.object(service.authentication, "create_refresh_token", return_value="refresh"),
    ):
        token_pair = await service.login(
            LoginCredentials(
                email=authenticated_user.email,
                password="TestPassword2026!",
            )
        )

    assert token_pair.access_token == "access"
    update_last_sign_in_at.assert_awaited_once()
    assert update_last_sign_in_at.await_args.args[0] == str(authenticated_user.id)
