from pydantic import BaseModel


class LoginJsonRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
