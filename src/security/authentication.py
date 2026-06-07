from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError

from src.config import settings
from src.db import auth_queries
from src.models.auth.authentication import CurrentUser, TokenClaims

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def create_access_token(user: CurrentUser) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)

    return jwt.encode(
        {
            "sub": str(user.id),
            "company_id": str(user.company_id),
            "role": user.role,
            "exp": expire,
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user: CurrentUser) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    return jwt.encode(
        {
            "sub": str(user.id),
            "exp": expire,
            "type": "refresh",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> TokenClaims:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    return TokenClaims.model_validate(payload)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        claims = decode_token(token)

        if claims.type != "access":
            raise credentials_exception
    except (InvalidTokenError, ValueError):
        raise credentials_exception

    user = await auth_queries.get_user_by_id(str(claims.sub))

    if user is None:
        raise credentials_exception

    return user


async def require_admin(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user
