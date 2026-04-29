from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    status: str = "success"
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)
