from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.exceptions import AuthenticationFailed
from src.models.auth.authentication import TokenClaims
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
        patch.object(service.auth_queries, "get_user_by_id", AsyncMock(return_value=None)),
    ):
        with pytest.raises(AuthenticationFailed):
            await service.refresh("token")
