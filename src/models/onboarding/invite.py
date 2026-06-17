from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models.enums.user_role import UserRole


class InviteRecord(BaseModel):
    id: UUID
    email: str
    role: UserRole
    created_at: datetime
    expires_at: datetime
    is_accepted: bool


class InviteCreated(BaseModel):
    id: UUID
    email: str
    role: UserRole
    created_at: datetime
