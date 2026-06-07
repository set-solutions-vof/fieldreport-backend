from typing import Annotated

from fastapi import APIRouter, Depends

from src.http.v1.response.team import TeamMemberResponse
from src.models.auth.authentication import CurrentUser
from src.security.authentication import require_admin
from src.services import team

router = APIRouter(tags=["Team"])


@router.get(
    "/api/v1/team/members",
    response_model=list[TeamMemberResponse],
    summary="List team members",
    description="Returns users for the current company.",
)
async def list_team_members(
    current_user: Annotated[CurrentUser, Depends(require_admin)],
) -> list[TeamMemberResponse]:
    members = await team.list_team_members(str(current_user.company_id))

    return [TeamMemberResponse.model_validate(member.model_dump()) for member in members]
