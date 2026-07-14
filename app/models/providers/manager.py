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
        providers: dict[str, AIProvider],
        default_provider: str = "openrouter",
    ) -> None:
        if not providers:
            raise ValueError("At least one provider must be configured")
        if default_provider not in providers:
            default_provider = next(iter(providers))
        self._providers = providers
        self._active = default_provider
        logger.info(
            "ProviderManager initialized",
            providers=list(providers.keys()),
            default=default_provider,
        )

    @property
    def active_provider_name(self) -> str:
        return self._active

    @property
    def active_provider(self) -> AIProvider:
        return self._providers[self._active]

    def set_provider(self, name: str) -> None:
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}. Available: {list(self._providers.keys())}")
        self._active = name
        logger.info("Provider switched", provider=name)

    def get_provider(self, name: str | None = None) -> AIProvider:
        key = name or self._active
        if key not in self._providers:
            raise ValueError(f"Unknown provider: {key}")
        return self._providers[key]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def list_models(self, provider_name: str | None = None) -> list[str]:
        p = self.get_provider(provider_name)
        return p.list_models()

    def set_model(self, model: str, provider_name: str | None = None) -> None:
        p = self.get_provider(provider_name)
        p.current_model = model
        logger.info("Model changed", provider=p.provider_name, model=model)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        provider_name: str | None = None,
    ) -> str:
        provider = self.get_provider(provider_name)
        try:
            return await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning(
                "Primary provider failed, trying fallback",
                provider=provider.provider_name,
                error=str(e),
            )
            fallback = self._find_fallback(provider.provider_name)
            if fallback:
                return await fallback.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            raise RuntimeError(
                f"All providers failed. Last error: {e}"
            ) from e

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        provider_name: str | None = None,
    ) -> AsyncIterator[str]:
        provider = self.get_provider(provider_name)
        try:
            async for chunk in provider.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk
        except Exception as e:
            logger.warning(
                "Primary provider stream failed, trying fallback",
                provider=provider.provider_name,
                error=str(e),
            )
            fallback = self._find_fallback(provider.provider_name)
            if fallback:
                async for chunk in fallback.generate_stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                ):
                    yield chunk
            else:
                raise RuntimeError(
                    f"All providers failed. Last error: {e}"
                ) from e

    async def health_check_all(self) -> dict[str, ProviderHealth]:
        results = {}
        for name, provider in self._providers.items():
            results[name] = await provider.health_check()
        return results

    async def health_check(self, provider_name: str | None = None) -> ProviderHealth:
        provider = self.get_provider(provider_name)
        return await provider.health_check()

    def _find_fallback(self, failed_provider: str) -> AIProvider | None:
        for name, provider in self._providers.items():
            if name != failed_provider:
                logger.info("Selected fallback provider", provider=name)
                return provider
        return None
