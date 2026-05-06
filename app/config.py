from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    secret_key: str
    allowed_origins: list[str] = ["http://localhost:3000"]

    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str

    access_token_expire_minutes: int = 3
    refresh_token_expire_minutes: int = 5

    database_url: str
    frontend_url: str

    admin_username: str


settings = Settings()
