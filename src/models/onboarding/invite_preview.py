from pydantic import BaseModel

from src.models.enums.user_role import UserRole


class InvitePreview(BaseModel):
    email: str
    role: UserRole
    company_name: str
