from uuid import UUID

from pydantic import BaseModel

from src.models.auth.authentication import UserRole


class CurrentUserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    company_id: UUID
