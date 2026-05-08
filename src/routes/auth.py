from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from src.http.v1.request.auth import LoginJsonRequest, RefreshTokenRequest
from src.http.v1.response.auth import RefreshTokenResponse, TokenResponse
from src.http.v1.response.user import CurrentUserResponse
from src.models.auth.authentication import CurrentUser, LoginCredentials
from src.security.authentication import AuthenticationError, get_current_user
from src.services import authentication

router = APIRouter(prefix="/api/v1/auth")


@router.post("/login", response_model=TokenResponse)
async def login_form(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> TokenResponse:
    try:
        token_pair = await authentication.login(
            LoginCredentials(email=form_data.username, password=form_data.password)
        )
    except authentication.InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse.model_validate(token_pair.model_dump())


@router.post("/login/json", response_model=TokenResponse)
async def login_json(request_body: LoginJsonRequest) -> TokenResponse:
    try:
        token_pair = await authentication.login(
            LoginCredentials(email=request_body.email, password=request_body.password)
        )
    except authentication.InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return TokenResponse.model_validate(token_pair.model_dump())


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request_body: RefreshTokenRequest) -> RefreshTokenResponse:
    try:
        refreshed_token = await authentication.refresh(request_body.refresh_token)
    except (authentication.InvalidCredentialsError, AuthenticationError):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return RefreshTokenResponse.model_validate(refreshed_token.model_dump())


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user.model_dump())
