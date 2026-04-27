from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_env: str = "dev"
    cors_origins: str = "http://localhost:3000"
    secret_key: str = "dev-secret-key-change-in-production-min-32"
    access_token_expire_minutes: int = 60
    internal_api_key: str = "dev-internal-key"

    database_url: str = (
        "postgresql+psycopg://whatcommerce:whatcommerce@127.0.0.1:5433/whatcommerce"
    )

    bootstrap_admin: bool = False
    admin_bootstrap_email: str | None = None
    admin_bootstrap_password: str | None = None

    paystack_secret_key: str | None = None
    paystack_webhook_secret: str | None = None

    whatsapp_bridge_dispatch_url: str | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"
    openai_transcribe_model: str = "whisper-1"
    store_manager_max_tool_rounds: int = 6
    inbound_media_max_bytes: int = 5_242_880
    conversation_history_max_events: int = 32

    onboarding_system_prompt_path: str | None = None

    agent_input_guard_enabled: bool = True
    openai_guard_model: str | None = None
    agent_input_guard_max_context_chars: int = 4000
    agent_input_guard_prompt_path: str | None = None

    openai_output_guard_model: str | None = None
    openai_humanizer_model: str | None = None

    openai_store_analyst_model: str | None = None
    openai_store_intent_model: str | None = None
    store_analyst_prompt_path: str | None = None

    openai_embedding_model: str = "text-embedding-3-small"
    knowledge_chunk_max_chars: int = 900
    knowledge_chunk_overlap: int = 120
    knowledge_search_top_k: int = 5
    knowledge_upload_max_bytes: int = 10_485_760

    product_upload_dir: str = "data/product_uploads"
    product_uploads_s3_bucket: str | None = None
    product_uploads_s3_region: str | None = None
    product_uploads_s3_prefix: str = "products"
    public_api_base_url: str | None = None

    @field_validator("secret_key", mode="before")
    @classmethod
    def strip_secret(cls, v: str) -> str:
        if not v or (isinstance(v, str) and len(v) < 16):
            raise ValueError("SECRET_KEY must be at least 16 characters")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
