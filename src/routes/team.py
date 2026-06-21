from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from src.exceptions import InviteAlreadyExists, InviteEmailDeliveryFailed
from src.http.v1.request.team import CreateTeamUserRequest, UpdateTeamUserRequest
from src.http.v1.response.team import TeamUserResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import require_admin
from src.services import invites, team

router = APIRouter(tags=["Team"])


@router.get(
    "/api/v1/team/users",
    response_model=list[TeamUserResponse],
    summary="List team users",
    description="Returns active members and pending invites for the current company.",
)
async def list_team_users(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> list[TeamUserResponse]:
    users = await team.list_team_users(str(current_user.company_id))

    return [TeamUserResponse.model_validate(user.model_dump()) for user in users]


@router.post(
    "/api/v1/team/users",
    response_model=TeamUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite team user",
    description="Creates a pending invite for a new team user.",
)
async def create_team_user(
    request_body: CreateTeamUserRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TeamUserResponse:
    first_name = request_body.first_name.strip()
    last_name = request_body.last_name.strip()

    if first_name == "" or last_name == "":
        raise HTTPException(status_code=422, detail="first_name and last_name are required")

    try:
        user, email_delivery = await team.create_team_user(
            str(current_user.company_id),
            first_name,
            last_name,
            request_body.email,
            request_body.role,
        )
    except InviteAlreadyExists:
        raise HTTPException(status_code=409, detail="Invite already exists")
    except InviteEmailDeliveryFailed:
        raise HTTPException(status_code=502, detail="Invite email could not be sent")

    background_tasks.add_task(invites.deliver_invite_email, email_delivery)

    return TeamUserResponse.model_validate(user.model_dump())


@router.get(
    "/api/v1/team/users/{user_id}",
    response_model=TeamUserResponse,
    summary="Get team user",
    description="Returns a team member or pending invite by id.",
)
async def get_team_user(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TeamUserResponse:
    user = await team.get_team_user(str(current_user.company_id), str(user_id))

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return TeamUserResponse.model_validate(user.model_dump())


@router.patch(
    "/api/v1/team/users/{user_id}",
    response_model=TeamUserResponse,
    summary="Update team user",
    description="Updates a team member or pending invite.",
)
async def update_team_user(
    user_id: UUID,
    request_body: UpdateTeamUserRequest,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> TeamUserResponse:
    first_name = request_body.first_name.strip()
    last_name = request_body.last_name.strip()

    if first_name == "" or last_name == "":
        raise HTTPException(status_code=422, detail="first_name and last_name are required")

    user = await team.update_team_user(
        str(current_user.company_id),
        str(user_id),
        first_name,
        last_name,
        request_body.role,
    )

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return TeamUserResponse.model_validate(user.model_dump())


@router.delete(
    "/api/v1/team/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete team user",
    description="Deletes a team member or revokes a pending invite.",
)
async def delete_team_user(
    user_id: UUID,
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> Response:
    if str(user_id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    was_deleted = await team.delete_team_user(str(current_user.company_id), str(user_id))

    if not was_deleted:
        raise HTTPException(status_code=404, detail="User not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
