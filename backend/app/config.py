"""Application configuration via Pydantic v2 Settings.

Supports environment separation:
  APP_ENV=development  → loads .env.development
  APP_ENV=production   → loads .env.production
  (default)            → loads .env
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

PROJECT_ROOT = Path(__file__).parent.parent.parent


class DatabaseSettings(BaseSettings):
    """Database connection pool configuration."""

    database_url: str = Field(
        default="",
        description="PostgreSQL connection URL. Must be set via environment variable.",
    )
    db_pool_size: int = Field(20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(10, alias="DB_MAX_OVERFLOW")
    db_pool_recycle: int = Field(1800, alias="DB_POOL_RECYCLE")
    db_pool_pre_ping: bool = Field(True, alias="DB_POOL_PRE_PING")
    db_pool_timeout: int = Field(30, alias="DB_POOL_TIMEOUT")

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")


class ChromaSettings(BaseSettings):
    """ChromaDB / embedding configuration."""

    chroma_persist_dir: str = Field("./chroma_data", alias="CHROMA_PERSIST_DIR")
    embedding_model: str = Field("BAAI/bge-small-zh-v1.5", alias="EMBEDDING_MODEL")

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")


class Settings(BaseSettings):
    """Application settings loaded from environment variables with .env file support."""

    model_config = SettingsConfigDict(
        env_file=f".env.{os.getenv('APP_ENV', 'development')}",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──
    app_name: str = "GraphNovel Studio"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # ── Logging ──
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = str(PROJECT_ROOT / "logs" / "app.log")
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_backup_count: int = 30

    # ── Database ──
    database: DatabaseSettings = DatabaseSettings()

    # ── CORS ──
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── ChromaDB / Embedding ──
    chroma: ChromaSettings = ChromaSettings()

    # ── AI Providers ──

    # DeepSeek (via OpenAI-compatible)
    openai_api_key: Optional[str] = Field(None, validation_alias="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(None, validation_alias="OPENAI_API_BASE")

    # Anthropic Claude
    anthropic_api_key: Optional[str] = Field(None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_base_url: Optional[str] = Field(None, validation_alias="ANTHROPIC_BASE_URL")

    # Google Gemini
    google_api_key: Optional[str] = Field(None, validation_alias="GOOGLE_API_KEY")

    # Qwen (Tongyi Qianwen) — multimodal: text + image
    qwen_api_key: Optional[str] = Field(None, validation_alias="Qwen_API_KEY")
    qwen_base_url: Optional[str] = Field(None, validation_alias="Qwen_API_BASE")

    # Kimi (Moonshot)
    kimi_api_key: Optional[str] = Field(None, validation_alias="kimi_API_KEY")
    kimi_base_url: Optional[str] = Field(None, validation_alias="kimi_API_BASE")

    # Tavily (web search)
    tavily_api_key: Optional[str] = None

    # HuggingFace
    hf_token: Optional[str] = None

    # ── AI Defaults ──
    default_llm_provider: str = "deepseek"
    default_llm_model: str = "deepseek-v4-pro"
    default_temperature: float = 0.7
    default_max_tokens: int = 32000

    # ── Image Generation ──
    image_provider: str = "qwen"
    image_model: str = "qwen-vl-max"

    # ── Redis ──
    redis_url: str = "redis://localhost:6379/0"

    # ── Properties ──

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        if self.debug:
            return ["*"]
        return origins

    @property
    def available_providers(self) -> list[str]:
        """List providers that have API keys configured."""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
            providers.append("deepseek")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.google_api_key:
            providers.append("gemini")
        if self.qwen_api_key:
            providers.append("qwen")
        if self.kimi_api_key:
            providers.append("kimi")
        return providers

    def get_provider_config(self, provider: str) -> dict:
        """Get API key and base URL for a given provider."""
        provider_map = {
            "openai":    (self.openai_api_key, self.openai_base_url),
            "deepseek":  (self.openai_api_key, self.openai_base_url),
            "anthropic": (self.anthropic_api_key, self.anthropic_base_url),
            "gemini":    (self.google_api_key, None),
            "qwen":      (self.qwen_api_key, self.qwen_base_url),
            "kimi":      (self.kimi_api_key, self.kimi_base_url),
        }
        key, url = provider_map.get(provider, (None, None))
        return {"api_key": key, "base_url": url}

    # ── Backward-compatible aliases (old code uses flat settings.database_url etc.) ──

    @property
    def database_url(self) -> str:
        return self.database.database_url

    @property
    def chroma_persist_dir(self) -> str:
        return self.chroma.chroma_persist_dir

    @property
    def embedding_model(self) -> str:
        return self.chroma.embedding_model

    def check_security(self) -> list[str]:
        """Check for security issues in configuration. Returns list of warnings."""
        warnings = []
        if self.database.database_url and "langnovel123" in self.database.database_url:
            warnings.append("Default database password 'langnovel123' detected! Change it immediately.")
        if not self.debug and not os.path.exists(".env.production"):
            warnings.append("Production mode without .env.production file.")
        return warnings


settings = Settings()


# ── Startup security check ──────────────────────────────────────────────────

_security_warnings = settings.check_security()
if _security_warnings:
    import logging
    _log = logging.getLogger(__name__)
    for w in _security_warnings:
        _log.warning("SECURITY: %s", w)
