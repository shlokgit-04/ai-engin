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
    port: int = 8000

    cors_origins: list[str] = ["*"]

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"

    openrouter_api_keys: str = ""
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

    default_provider: str = "openrouter"

    @property
    def openrouter_keys(self) -> list[str]:
        keys = [
            self.openrouter_api_key_1,
            self.openrouter_api_key_2,
            self.openrouter_api_key_3,
            self.openrouter_api_key_4,
            self.openrouter_api_key_5,
            self.openrouter_api_key_6,
            self.openrouter_api_key_7,
            self.openrouter_api_key_8,
            self.openrouter_api_key_9,
            self.openrouter_api_key_10,
        ]
        if self.openrouter_api_keys:
            keys.insert(0, self.openrouter_api_keys)
        return [k for k in keys if k.strip()]

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "nurofin"

    backend_base_url: str = "http://localhost:8000/api/v1"


settings = Settings()
