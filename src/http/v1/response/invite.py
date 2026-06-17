from pydantic import BaseModel, ConfigDict

from src.models.enums.user_role import UserRole


class InvitePreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str
    role: UserRole
    company_name: str
