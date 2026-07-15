from app.models.base import BaseLLM
from app.models.providers.manager import ProviderManager
from app.core.logging import logger


class ProviderManagerLLM(BaseLLM):
    """Adapter wrapping ProviderManager as a BaseLLM for backward compatibility."""

    def __init__(self, manager: ProviderManager) -> None:
        self._manager = manager

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        return await self._manager.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def health_check(self) -> bool:
        try:
            result = await self._manager.health_check()
            return result.healthy
        except Exception:
            return False
