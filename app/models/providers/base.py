from abc import ABC, abstractmethod
from typing import AsyncIterator

from pydantic import BaseModel


class ProviderHealth(BaseModel):
    healthy: bool
    provider: str
    message: str = ""


class AIProvider(ABC):
    """Abstract base class for all AI providers.

    Every provider (OpenRouter, Ollama, Gemini, etc.) must implement
    this interface. The ProviderManager calls these methods — no module
    should call a provider directly.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Non-streaming generation. Returns the full response text."""

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Streaming generation. Yields text chunks."""

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Check if this provider is reachable and functional."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return available model identifiers for this provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Canonical name of the provider (e.g. 'openrouter', 'ollama')."""

    @property
    def current_model(self) -> str:
        """Currently selected model identifier."""
        return getattr(self, "_model", "unknown")

    @current_model.setter
    def current_model(self, model: str) -> None:
        self._model = model
