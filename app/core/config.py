from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Nurofin Executive AI Engine"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_prefix: str = "/api/v1"

    host: str = "0.0.0.0"
    port: int = 8001

    cors_origins: list[str] = ["*"]

    # Gemini (legacy — kept for backward compatibility)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # OpenRouter (up to 10 keys)
    openrouter_api_key_1: str = ""
    openrouter_api_key_2: str = ""
    openrouter_api_key_3: str = ""
    openrouter_api_key_4: str = ""
    openrouter_api_key_5: str = ""
    openrouter_api_key_6: str = ""
    openrouter_api_key_7: str = ""
    openrouter_api_key_8: str = ""
    openrouter_api_key_9: str = ""
    openrouter_api_key_10: str = ""
    openrouter_model: str = "openai/gpt-oss-20b:free"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    # Provider selection
    default_provider: str = "openrouter"
    default_model: str = "openai/gpt-oss-20b:free"

    # Qdrant (knowledge pipeline)
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "nurofin"

    # Backend integration
    backend_base_url: str = "http://localhost:8000"

    @property
    def openrouter_api_keys(self) -> list[str]:
        """Return all non-empty OpenRouter API keys."""
        return [
            getattr(self, f"openrouter_api_key_{i}")
            for i in range(1, 11)
            if getattr(self, f"openrouter_api_key_{i}")
        ]


settings = Settings()
