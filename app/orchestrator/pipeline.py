from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.models.base import BaseLLM
from app.core.logging import logger


FEATURE_PLACEHOLDER = "Feature planned for upcoming implementation."


class ExecutionPipeline:
    def __init__(
        self,
        gemini: BaseLLM,
        ollama: BaseLLM,
        knowledge_pipeline: DocumentIntelligencePipeline,
    ) -> None:
        self._gemini = gemini
        self._ollama = ollama
        self._knowledge = knowledge_pipeline

    async def execute(self, category: RequestCategory, context: ExecutionContext) -> str:
        logger.debug(
            "Pipeline executing",
            category=category.value,
        )

        if category == RequestCategory.GENERAL_CHAT:
            return await self._gemini.generate_response(prompt=context.message)

        if category in (RequestCategory.COMPANY_KNOWLEDGE, RequestCategory.DOCUMENT_QUERY):
            return await self._knowledge.execute(context)

        return FEATURE_PLACEHOLDER
