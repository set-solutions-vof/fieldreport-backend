from pydantic import BaseModel, Field


class AcceptInviteRequest(BaseModel):
    password: str = Field(min_length=8)
