from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.enums.team_user_status import TeamUserStatus
from src.models.enums.user_role import UserRole


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    role: UserRole
    created_at: datetime


class TeamUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    role: UserRole
    status: TeamUserStatus
    created_at: datetime
    last_sign_in_at: datetime | None = None
