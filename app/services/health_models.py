import asyncio
from app.schemas.health_models import ModelsHealthResponse
from app.models.base import BaseLLM
from app.core.logging import logger


class ModelsHealthService:
    def __init__(self, gemini: BaseLLM, ollama: BaseLLM) -> None:
        self._gemini = gemini
        self._ollama = ollama

    async def check(self) -> ModelsHealthResponse:
        logger.info("Models health check requested")
        gemini_result, ollama_result = await asyncio.gather(
            self._gemini.health_check(),
            self._ollama.health_check(),
            return_exceptions=True,
        )
        return ModelsHealthResponse(
            gemini="healthy" if gemini_result is True else "unreachable",
            ollama="healthy" if ollama_result is True else "unreachable",
        )
