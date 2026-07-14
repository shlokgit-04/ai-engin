import asyncio
from app.schemas.health_models import ModelsHealthResponse, ProviderHealthInfo
from app.models.base import BaseLLM
from app.models.providers.manager import ProviderManager
from app.core.logging import logger


class ModelsHealthService:
    def __init__(
        self,
        provider_manager: ProviderManager,
        gemini: BaseLLM | None = None,
        ollama: BaseLLM | None = None,
    ) -> None:
        self._provider_manager = provider_manager
        self._gemini = gemini
        self._ollama = ollama

    async def check(self) -> ModelsHealthResponse:
        logger.info("Models health check requested")
        results = await self._provider_manager.health_check_all()

        response = ModelsHealthResponse(
            active_provider=self._provider_manager.active_provider_name,
        )

        for name, health in results.items():
            info = ProviderHealthInfo(
                status="healthy" if health.healthy else "unreachable",
                message=health.message,
            )
            if name == "openrouter":
                response.openrouter = info
            elif name == "ollama":
                response.ollama = info

        if self._gemini:
            try:
                gemini_ok = await self._gemini.health_check()
                response.gemini = "healthy" if gemini_ok else "unreachable"
            except Exception:
                response.gemini = "unreachable"

        return response
