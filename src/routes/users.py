from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.exceptions import PasswordIncorrect
from src.http.v1.request.user import ChangePasswordRequest, UpdateProfileRequest
from src.http.v1.response.user import CurrentUserResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import get_current_user
from src.services import users as users_service

router = APIRouter(tags=["Users"])


@router.patch(
    "/api/v1/users/me",
    response_model=CurrentUserResponse,
    summary="Update current user profile",
    description="Updates the authenticated user's display name.",
)
async def update_me(
    request_body: UpdateProfileRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUserResponse:
    name = request_body.name.strip()

    if not name:
        raise HTTPException(status_code=422, detail="name must not be blank")
    if len(name) > 100:
        raise HTTPException(status_code=422, detail="name must not exceed 100 characters")

    updated_user = await users_service.update_profile(current_user, name)

    return CurrentUserResponse.model_validate(updated_user)


@router.post(
    "/api/v1/users/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change current user password",
    description="Changes the authenticated user's password.",
)
async def change_password(
    request_body: ChangePasswordRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    if len(request_body.new_password) < 8:
        raise HTTPException(status_code=422, detail="password_too_short")

    try:
        await users_service.change_password(
            str(current_user.id),
            request_body.current_password,
            request_body.new_password,
        )
    except PasswordIncorrect:
        raise HTTPException(status_code=422, detail="current_password_incorrect")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
