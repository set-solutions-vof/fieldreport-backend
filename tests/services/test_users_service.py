from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import PasswordIncorrect
from src.models.auth.authentication import CurrentUser
from src.services import users as users_service


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector@example.com",
        name="Inspector",
        role="inspector",
    )


async def test_update_profile_updates_name_and_returns_current_user() -> None:
    current_user = build_current_user()

    with patch.object(
        users_service.db_queries,
        "update_user_name",
        AsyncMock(),
    ) as update_name:
        result = await users_service.update_profile(current_user, "Updated Inspector")

    assert result == current_user.model_copy(update={"name": "Updated Inspector"})
    update_name.assert_awaited_once_with(str(current_user.id), "Updated Inspector")


async def test_change_password_updates_hash_when_current_password_matches() -> None:
    user_id = str(uuid4())

    with (
        patch.object(
            users_service.db_queries,
            "get_user_password_hash",
            AsyncMock(return_value="stored-hash"),
        ) as get_hash,
        patch.object(users_service.bcrypt, "checkpw", return_value=True) as check_password,
        patch.object(users_service.bcrypt, "gensalt", return_value=b"salt") as generate_salt,
        patch.object(users_service.bcrypt, "hashpw", return_value=b"new-hash") as hash_password,
        patch.object(
            users_service.db_queries,
            "update_user_password",
            AsyncMock(),
        ) as update_password,
    ):
        await users_service.change_password(user_id, "current-password", "new-password")

    get_hash.assert_awaited_once_with(user_id)
    check_password.assert_called_once_with(b"current-password", b"stored-hash")
    generate_salt.assert_called_once_with()
    hash_password.assert_called_once_with(b"new-password", b"salt")
    update_password.assert_awaited_once_with(user_id, "new-hash")


async def test_change_password_raises_when_current_password_does_not_match() -> None:
    user_id = str(uuid4())

    with (
        patch.object(
            users_service.db_queries,
            "get_user_password_hash",
            AsyncMock(return_value="stored-hash"),
        ),
        patch.object(users_service.bcrypt, "checkpw", return_value=False),
        patch.object(
            users_service.db_queries,
            "update_user_password",
            AsyncMock(),
        ) as update_password,
    ):
        with pytest.raises(PasswordIncorrect):
            await users_service.change_password(user_id, "current-password", "new-password")

    update_password.assert_not_awaited()
