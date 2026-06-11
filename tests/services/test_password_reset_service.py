from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import InvalidResetToken, InviteEmailDeliveryFailed
from src.models.auth.authentication import AuthenticatedUser
from src.services import password_reset as password_reset_service


def build_authenticated_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="user@example.com",
        password_hash="old-hash",
        name="Demo User",
        role="admin",
    )


async def test_request_reset_returns_silently_when_user_is_missing() -> None:
    with (
        patch.object(
            password_reset_service.auth_queries,
            "get_user_by_email",
            AsyncMock(return_value=None),
        ),
        patch.object(
            password_reset_service.reset_queries, "create_reset_token", AsyncMock()
        ) as create,
        patch.object(
            password_reset_service, "send_password_reset_email", AsyncMock()
        ) as send_email,
    ):
        await password_reset_service.request_reset("missing@example.com")

    create.assert_not_awaited()
    send_email.assert_not_awaited()


async def test_request_reset_stores_hashed_token_and_sends_raw_token() -> None:
    user = build_authenticated_user()

    with (
        patch.object(
            password_reset_service.auth_queries,
            "get_user_by_email",
            AsyncMock(return_value=user),
        ),
        patch.object(
            password_reset_service.reset_queries,
            "create_reset_token",
            AsyncMock(),
        ) as create,
        patch.object(
            password_reset_service, "send_password_reset_email", AsyncMock()
        ) as send_email,
        patch.object(password_reset_service.secrets, "token_urlsafe", return_value="raw-token"),
    ):
        await password_reset_service.request_reset("user@example.com")

    create.assert_awaited_once()
    assert create.await_args.args[0] == str(user.id)
    assert create.await_args.args[1] == (
        "34d328009b123fbbb0dc93f18b3e6de1ecf7b1a5783c33dff7ffe1926f09e943"
    )
    send_email.assert_awaited_once_with(to_email="user@example.com", token="raw-token")


async def test_request_reset_raises_delivery_failed_when_email_fails() -> None:
    user = build_authenticated_user()

    with (
        patch.object(
            password_reset_service.auth_queries,
            "get_user_by_email",
            AsyncMock(return_value=user),
        ),
        patch.object(password_reset_service.reset_queries, "create_reset_token", AsyncMock()),
        patch.object(
            password_reset_service,
            "send_password_reset_email",
            AsyncMock(side_effect=RuntimeError("smtp failed")),
        ),
        patch.object(password_reset_service.secrets, "token_urlsafe", return_value="raw-token"),
    ):
        with pytest.raises(InviteEmailDeliveryFailed):
            await password_reset_service.request_reset("user@example.com")


async def test_confirm_reset_updates_password_and_marks_token_used() -> None:
    token_id = uuid4()
    user_id = uuid4()

    with (
        patch.object(
            password_reset_service.reset_queries,
            "get_valid_reset_token",
            AsyncMock(return_value={"id": token_id, "user_id": user_id}),
        ),
        patch.object(
            password_reset_service.user_queries,
            "update_user_password",
            AsyncMock(),
        ) as update_password,
        patch.object(
            password_reset_service.reset_queries,
            "mark_token_used",
            AsyncMock(),
        ) as mark_token_used,
        patch.object(password_reset_service.bcrypt, "gensalt", return_value=b"salt"),
        patch.object(password_reset_service.bcrypt, "hashpw", return_value=b"new-hash"),
    ):
        await password_reset_service.confirm_reset("raw-token", "NewPassword2026!")

    update_password.assert_awaited_once_with(str(user_id), "new-hash")
    mark_token_used.assert_awaited_once_with(str(token_id))


async def test_confirm_reset_raises_for_missing_token() -> None:
    with patch.object(
        password_reset_service.reset_queries,
        "get_valid_reset_token",
        AsyncMock(return_value=None),
    ):
        with pytest.raises(InvalidResetToken):
            await password_reset_service.confirm_reset("raw-token", "NewPassword2026!")
