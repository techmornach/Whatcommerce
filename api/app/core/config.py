from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://whatcommerce:whatcommerce@localhost:5433/whatcommerce"
    serper_api_key: Optional[str] = None
    internal_api_secret: str = "change-me-in-dev"
    paystack_secret_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    # Absolute base for links in WhatsApp (no trailing slash), e.g. https://api.yourdomain.com
    public_base_url: str = "http://localhost:8000"

    # Dashboard admins (Next.js /admin) — use a long random string in production
    admin_jwt_secret: str = "change-admin-jwt-in-dev"
    admin_jwt_algorithm: str = "HS256"
    admin_access_token_expire_minutes: int = 60 * 12

    # If set and no admin_users rows exist yet, create one super_admin on startup
    bootstrap_admin_email: Optional[str] = None
    bootstrap_admin_password: Optional[str] = None

    # Comma-separated browser origins for CORS (e.g. https://app.example.com or http://192.168.1.10:3000)
    cors_allow_origins: str = ""

    @property
    def database_url_sync(self) -> str:
        """Alembic uses a sync driver (psycopg3); the app runtime uses asyncpg."""
        if "+asyncpg" in self.database_url:
            return self.database_url.replace("postgresql+asyncpg", "postgresql+psycopg")
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
