from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.auth.authentication import UserRole


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: UserRole
    company_id: UUID
    company_name: str
