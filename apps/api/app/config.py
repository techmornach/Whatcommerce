from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    internal_secret: str = "change-me-in-dev"
    default_tenant_id: str = "dev-tenant-1"
    bridge_base_url: str = "http://127.0.0.1:3001"
    database_url: str | None = None


settings = Settings()
