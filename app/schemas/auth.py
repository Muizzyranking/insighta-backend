from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    status: str = "success"
    access_token: str
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str | None = Field(None, min_length=1)


class GitHubLoginQuery(BaseModel):
    state: str | None = Field(None, description="CSRF protection state")
    code_challenge: str | None = None
    code_challenge_method: str | None = "S256"
    code_verifier: str | None = None
    redirect_uri: str | None = None


class GithubCallbackQuery(BaseModel):
    code: str
    state: str
