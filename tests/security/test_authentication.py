from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.models.auth.authentication import CurrentUser
from src.security import authentication as security


def build_current_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="admin.user@example.com",
        first_name="Admin",
        last_name="User",
        role="admin",
    )


def build_inspector_user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        company_id=uuid4(),
        company_name="Demo Company",
        email="inspector.user@example.com",
        first_name="Inspector",
        last_name="User",
        role="inspector",
    )


def test_decode_token_returns_access_claims() -> None:
    current_user = build_current_user()
    token = security.create_access_token(current_user)

    claims = security.decode_token(token)

    assert claims.sub == current_user.id
    assert claims.company_id == current_user.company_id
    assert claims.role == current_user.role
    assert claims.type == "access"


def test_decode_token_returns_refresh_claims() -> None:
    current_user = build_current_user()
    token = security.create_refresh_token(current_user)

    claims = security.decode_token(token)

    assert claims.sub == current_user.id
    assert claims.type == "refresh"
    assert claims.company_id is None
    assert claims.role is None


def test_decode_token_raises_for_invalid_token() -> None:
    from jwt import InvalidTokenError

    with pytest.raises(InvalidTokenError):
        security.decode_token("invalid")


async def test_get_current_user_raises_for_refresh_token() -> None:
    current_user = build_current_user()
    refresh_token = security.create_refresh_token(current_user)

    with pytest.raises(HTTPException) as error:
        await security.get_current_user(refresh_token)

    assert error.value.status_code == 401


async def test_get_current_user_raises_for_invalid_token() -> None:
    with pytest.raises(HTTPException) as error:
        await security.get_current_user("invalid")

    assert error.value.status_code == 401


async def test_get_current_user_returns_repository_user() -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(security.queries, "get_user_by_id", AsyncMock(return_value=current_user)):
        user = await security.get_current_user(access_token)

    assert user == current_user


async def test_get_current_user_raises_when_repository_returns_none() -> None:
    current_user = build_current_user()
    access_token = security.create_access_token(current_user)

    with patch.object(security.queries, "get_user_by_id", AsyncMock(return_value=None)):
        with pytest.raises(HTTPException) as error:
            await security.get_current_user(access_token)

    assert error.value.status_code == 401


async def test_require_admin_raises_for_non_admin_user() -> None:
    current_user = build_inspector_user()

    with pytest.raises(HTTPException) as error:
        await security.require_admin(current_user)

    assert error.value.status_code == 403
    assert error.value.detail == "Admin access required"
