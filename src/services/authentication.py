from src.integrations import auth_repository
from src.models.auth.authentication import (
    CurrentUser,
    LoginCredentials,
    RefreshedAccessToken,
    TokenClaims,
    TokenPair,
)
from src.security import authentication


class InvalidCredentialsError(Exception):
    pass


async def login(credentials: LoginCredentials) -> TokenPair:
    user = await auth_repository.get_user_by_email(credentials.email)

    if user is None or not authentication.verify_password(credentials.password, user.password_hash):
        raise InvalidCredentialsError

    current_user = CurrentUser(
        id=user.id,
        company_id=user.company_id,
        email=user.email,
        name=user.name,
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
        raise InvalidCredentialsError

    current_user = await get_current_user(claims)

    return RefreshedAccessToken(
        access_token=authentication.create_access_token(current_user),
        token_type="bearer",
    )


async def get_current_user(claims: TokenClaims) -> CurrentUser:
    user = await auth_repository.get_user_by_id(str(claims.sub))

    if user is None:
        raise InvalidCredentialsError

    return user
