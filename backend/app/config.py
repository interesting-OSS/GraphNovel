"""Application configuration via Pydantic Settings."""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # Application
    app_name: str = "LangNovel Studio"
    app_version: str = "1.0.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Logging
    log_level: str = "INFO"
    log_to_file: bool = True
    log_file_path: str = str(PROJECT_ROOT / "logs" / "app.log")
    log_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_backup_count: int = 30
    log_message_max_chars: int = 2000

    # Database
    database_url: str = "postgresql+asyncpg://langnovel:langnovel123@localhost:5432/langnovel_db"

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── AI Providers ──

    # DeepSeek (via OpenAI-compatible)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None

    # Anthropic Claude
    anthropic_api_key: Optional[str] = None
    anthropic_base_url: Optional[str] = None

    # Google Gemini
    google_api_key: Optional[str] = None

    # Qwen (Tongyi Qianwen) — multimodal: text + image
    qwen_api_key: Optional[str] = None
    qwen_base_url: Optional[str] = None

    # Kimi (Moonshot)
    kimi_api_key: Optional[str] = None
    kimi_base_url: Optional[str] = None

    # Tavily (web search)
    tavily_api_key: Optional[str] = None

    # HuggingFace
    hf_token: Optional[str] = None

    # ── AI Defaults ──
    default_ai_provider: str = "openai"
    default_ai_model: str = "gpt-4o"
    default_temperature: float = 0.7
    default_max_tokens: int = 32000

    # ── Image Generation ──
    image_provider: str = "qwen"  # Qwen multimodal for cover generation
    image_model: str = "qwen-vl-max"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"

    # Embedding
    embedding_model: str = "BAAI/bge-small-zh-v1.5"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

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


settings = Settings()
