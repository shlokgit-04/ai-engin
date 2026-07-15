from typing import AsyncIterator

from app.models.providers.base import AIProvider, ProviderHealth
from app.core.logging import logger


class ProviderManager:
    """Central manager for AI provider routing.

    Responsibilities:
    - Current active provider
    - Provider switching
    - Retry with fallback
    - Provider health
    - Future provider support
    """

    def __init__(
        self,
        providers: dict[str, AIProvider] | None = None,
        default_provider: str | None = None,
    ) -> None:
        self._providers: dict[str, AIProvider] = providers or {}
        if not self._providers:
            raise ValueError("At least one provider must be configured")
        self._active: str = default_provider or next(iter(self._providers))
        if self._active not in self._providers:
            self._active = next(iter(self._providers))
        logger.info(
            "ProviderManager initialized",
            providers=list(self._providers.keys()),
            active=self._active,
        )

    @property
    def active_provider_name(self) -> str:
        return self._active

    @property
    def active_provider(self) -> AIProvider:
        return self._providers[self._active]

    def set_provider(self, provider: str) -> None:
        if provider not in self._providers:
            available = list(self._providers.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")
        self._active = provider
        logger.info("Provider switched", provider=provider)

    def get_provider(self, name: str | None = None) -> AIProvider:
        key = name or self._active
        if key not in self._providers:
            raise ValueError(f"Unknown provider: {key}")
        return self._providers[key]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def list_models(self, provider: str | None = None) -> list[str]:
        return self.get_provider(provider).list_models()

    def set_model(self, provider: str, model: str) -> None:
        p = self.get_provider(provider)
        p.current_model = model
        logger.info("Model changed", provider=provider, model=model)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        failed_provider: str | None = None,
    ) -> str:
        try:
            provider = self.get_provider()
            return await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            logger.warning(
                "Primary provider failed, trying fallback",
                provider=self._active,
                error=str(exc),
            )
            fallback = self._find_fallback(exclude=failed_provider)
            if fallback:
                return await fallback.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise RuntimeError(f"All providers failed. Last error: {exc}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        failed_provider: str | None = None,
    ) -> AsyncIterator[str]:
        try:
            provider = self.get_provider()
            async for chunk in provider.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
        except Exception as exc:
            logger.warning(
                "Primary provider stream failed, trying fallback",
                provider=self._active,
                error=str(exc),
            )
            fallback = self._find_fallback(exclude=failed_provider)
            if fallback:
                async for chunk in fallback.generate_stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
            else:
                raise RuntimeError(f"All providers failed. Last error: {exc}")

    async def health_check_all(self) -> dict[str, ProviderHealth]:
        results: dict[str, ProviderHealth] = {}
        for name, provider in self._providers.items():
            results[name] = await provider.health_check()
        return results

    async def health_check(self, provider: str | None = None) -> ProviderHealth:
        p = self.get_provider(provider)
        return await p.health_check()

    def _find_fallback(self, exclude: str | None = None) -> AIProvider | None:
        for name, provider in self._providers.items():
            if name != self._active and name != exclude:
                logger.info("Selected fallback provider", provider=name)
                return provider
        return None
