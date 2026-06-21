from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.enums.user_role import UserRole


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: str
    role: UserRole
    company_id: UUID
    company_name: str
