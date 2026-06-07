from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.models.enums.user_role import UserRole


class InviteDetails(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str
    email: str
    role: UserRole
    is_accepted: bool
    expires_at: datetime
