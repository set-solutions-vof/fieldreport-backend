import os
from datetime import UTC, datetime

import bcrypt

from src.db.auth import queries
from src.exceptions import AuthenticationFailed
from src.models.auth.authentication import (
    CurrentUser,
    LoginCredentials,
    RefreshedAccessToken,
    TokenPair,
)
from src.security import authentication


async def login(credentials: LoginCredentials) -> TokenPair:
    user = await queries.get_user_by_email(credentials.email)

    if user is None:
        bcrypt.checkpw(
            credentials.password.encode(),
            bcrypt.hashpw(os.urandom(16), bcrypt.gensalt()),
        )
        raise AuthenticationFailed()

    if not authentication.verify_password(credentials.password, user.password_hash):
        raise AuthenticationFailed()

    signed_in_at = datetime.now(UTC)
    await queries.update_last_sign_in_at(str(user.id), signed_in_at)

    current_user = CurrentUser(
        id=user.id,
        company_id=user.company_id,
        company_name=user.company_name,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )

    return TokenPair(
        access_token=authentication.create_access_token(current_user),
        refresh_token=authentication.create_refresh_token(current_user),
        token_type="bearer",
    )


async def refresh(refresh_token: str) -> RefreshedAccessToken:
    claims = authentication.decode_token(refresh_token)

    if claims.type != "refresh":
        raise AuthenticationFailed()

    current_user = await queries.get_user_by_id(str(claims.sub))

    if current_user is None:
        raise AuthenticationFailed()

    return RefreshedAccessToken(
        access_token=authentication.create_access_token(current_user),
        token_type="bearer",
    )
