from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status
from jwt import InvalidTokenError

from src.exceptions import AuthenticationFailed, InvalidResetToken, InviteEmailDeliveryFailed
from src.http.v1.request.auth import (
    LoginFormRequest,
    LoginJsonRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
    RefreshTokenRequest,
)
from src.http.v1.response.auth import RefreshTokenResponse, TokenResponse
from src.http.v1.response.user import CurrentUserResponse
from src.models.auth.authentication import CurrentUser, LoginCredentials
from src.security.authentication import get_current_user
from src.services import authentication, password_reset

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
    except AuthenticationFailed:
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
    except AuthenticationFailed:
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
    except (AuthenticationFailed, InvalidTokenError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return RefreshTokenResponse.model_validate(refreshed_token)


@router.post(
    "/api/v1/auth/password-reset/request",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Request password reset",
    description="Sends a password reset email when the email address exists.",
)
async def request_password_reset(request_body: PasswordResetRequestRequest) -> None:
    try:
        await password_reset.request_reset(request_body.email)
    except InviteEmailDeliveryFailed:
        return


@router.post(
    "/api/v1/auth/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirm password reset",
    description="Sets a new password using a valid password reset token.",
)
async def confirm_password_reset(request_body: PasswordResetConfirmRequest) -> None:
    if len(request_body.new_password) < 8:
        raise HTTPException(status_code=422, detail="password_too_short")

    try:
        await password_reset.confirm_reset(request_body.token, request_body.new_password)
    except InvalidResetToken:
        raise HTTPException(status_code=422, detail="invalid_or_expired_token")


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
