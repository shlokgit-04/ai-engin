from typing import AsyncIterator

from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.models.base import BaseLLM
from app.models.providers.manager import ProviderManager
from app.core.logging import logger


FEATURE_PLACEHOLDER = "Feature planned for upcoming implementation."


class ExecutionPipeline:
    def __init__(
        self,
        provider_manager: ProviderManager,
        gemini: BaseLLM | None = None,
        ollama: BaseLLM | None = None,
        knowledge_pipeline: DocumentIntelligencePipeline | None = None,
    ) -> None:
        self._provider_manager = provider_manager
        self._gemini = gemini
        self._ollama = ollama
        self._knowledge = knowledge_pipeline or DocumentIntelligencePipeline()

    async def execute(self, category: RequestCategory, context: ExecutionContext) -> str:
        logger.debug(
            "Pipeline executing",
            category=category.value,
            provider=self._provider_manager.active_provider_name,
        )

        if category == RequestCategory.GENERAL_CHAT:
            return await self._provider_manager.generate(prompt=context.message)

        if category in (RequestCategory.COMPANY_KNOWLEDGE, RequestCategory.DOCUMENT_QUERY):
            return await self._knowledge.execute(context)

        return FEATURE_PLACEHOLDER

    async def execute_stream(
        self, category: RequestCategory, context: ExecutionContext
    ) -> AsyncIterator[str]:
        logger.debug(
            "Pipeline executing (stream)",
            category=category.value,
            provider=self._provider_manager.active_provider_name,
        )

        if category == RequestCategory.GENERAL_CHAT:
            async for chunk in self._provider_manager.generate_stream(prompt=context.message):
                yield chunk
            return

        result = await self.execute(category, context)
        yield result

    def set_provider_model(self, provider_name: str, model: str) -> None:
        """Switch provider and/or model at runtime."""
        if provider_name:
            self._provider_manager.set_provider(provider_name)
        if model:
            self._provider_manager.set_model(model)

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        provider_name: str | None = None,
    ) -> str:
        return await self._provider_manager.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name=provider_name,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        provider_name: str | None = None,
    ) -> AsyncIterator[str]:
        async for chunk in self._provider_manager.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            provider_name=provider_name,
        ):
            yield chunk
