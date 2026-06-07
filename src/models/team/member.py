from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models.enums.user_role import UserRole


class TeamMember(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime
