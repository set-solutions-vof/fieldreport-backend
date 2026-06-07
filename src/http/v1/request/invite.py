from pydantic import BaseModel


class AcceptInviteRequest(BaseModel):
    name: str
    password: str
