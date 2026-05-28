from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException
from jwt import InvalidTokenError

from src.http.v1.request.auth import LoginFormRequest, LoginJsonRequest, RefreshTokenRequest
from src.http.v1.response.auth import RefreshTokenResponse, TokenResponse
from src.http.v1.response.user import CurrentUserResponse
from src.models.auth.authentication import CurrentUser, LoginCredentials
from src.security.authentication import get_current_user
from src.services import authentication

router = APIRouter(tags=["Auth"])


@router.post(
    "/api/v1/auth/login",
    response_model=TokenResponse,
    summary="Login (form)",
    description="Authenticate with email and password using OAuth2 form fields.",
)
async def login_form(
    form_data: Annotated[LoginFormRequest, Form()],
) -> TokenResponse:
    try:
        token_pair = await authentication.login(
            LoginCredentials(email=form_data.username, password=form_data.password)
        )
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse.model_validate(token_pair)


@router.post(
    "/api/v1/auth/login/json",
    response_model=TokenResponse,
    summary="Login (JSON)",
    description="Authenticate with email and password in a JSON request body.",
)
async def login_json(request_body: LoginJsonRequest) -> TokenResponse:
    try:
        token_pair = await authentication.login(
            LoginCredentials(email=request_body.email, password=request_body.password)
        )
    except PermissionError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse.model_validate(token_pair)


@router.post(
    "/api/v1/auth/refresh",
    response_model=RefreshTokenResponse,
    summary="Refresh token",
    description="Exchange a valid refresh token for a new access token.",
)
async def refresh_token(request_body: RefreshTokenRequest) -> RefreshTokenResponse:
    try:
        refreshed_token = await authentication.refresh(request_body.refresh_token)
    except (PermissionError, InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return RefreshTokenResponse.model_validate(refreshed_token)


@router.get(
    "/api/v1/auth/me",
    response_model=CurrentUserResponse,
    summary="Current user",
    description="Returns the authenticated user's profile.",
)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
