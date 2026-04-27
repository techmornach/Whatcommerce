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

    # POST from API to Node bridge (e.g. http://127.0.0.1:3001/dispatch) for outbound WA
    whatsapp_bridge_dispatch_url: str | None = None

    # OpenAI (store manager on WhatsApp for active tenants)
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"
    openai_transcribe_model: str = "whisper-1"
    store_manager_max_tool_rounds: int = 6
    inbound_media_max_bytes: int = 5_242_880
    conversation_history_max_events: int = 32

    # Optional path to a custom onboarding system prompt (Markdown). If unset, uses
    # bundled `app/prompts/onboarding_system.md`.
    onboarding_system_prompt_path: str | None = None

    # Input guard (jailbreak / prompt-injection) on the *latest* user message; uses
    # recent thread as context. Fails open if the guard call errors.
    agent_input_guard_enabled: bool = True
    openai_guard_model: str | None = None
    # Max characters of formatted transcript sent to the guard (tail-preserved if truncated)
    agent_input_guard_max_context_chars: int = 4000
    # Optional override path for guard prompt (default: app/prompts/agent_input_guard.md)
    agent_input_guard_prompt_path: str | None = None

    # Output guard + humanizer (second pass on assistant text before WhatsApp send).
    # Model names default to `openai_model` when unset.
    openai_output_guard_model: str | None = None
    openai_humanizer_model: str | None = None

    # Optional model for brand/feedback; defaults to openai_model.
    openai_store_analyst_model: str | None = None
    # Classifier: analyst vs operations; defaults to openai_model.
    openai_store_intent_model: str | None = None
    # Optional path to custom store analyst prompt (default: app/prompts/store_analyst.md)
    store_analyst_prompt_path: str | None = None

    # Knowledge base (RAG for store agent; admin CRUD)
    openai_embedding_model: str = "text-embedding-3-small"
    knowledge_chunk_max_chars: int = 900
    knowledge_chunk_overlap: int = 120
    knowledge_search_top_k: int = 5
    knowledge_upload_max_bytes: int = 10_485_760  # 10 MB; PDF / MD / txt

    # Product images: local folder (dev); production can use a CDN or S3 with same URL prefix.
    product_upload_dir: str = "data/product_uploads"
    product_uploads_s3_bucket: str | None = None
    product_uploads_s3_region: str | None = None
    product_uploads_s3_prefix: str = "products"
    # If set, stored image URLs are absolute (e.g. https://api.example.com) for catalog links.
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
