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
        provider_llm: BaseLLM | None = None,
    ) -> None:
        self._gemini = gemini
        self._ollama = ollama
        self._knowledge = knowledge_pipeline
        self._provider_llm = provider_llm

    async def execute(self, category: RequestCategory, context: ExecutionContext) -> str:
        logger.debug(
            "Pipeline executing",
            category=category.value,
        )

        if category == RequestCategory.GENERAL_CHAT:
            if self._provider_llm:
                try:
                    return await self._provider_llm.generate_response(prompt=context.message)
                except Exception as e:
                    logger.warning("Provider LLM failed, falling back to Gemini", error=str(e))

            try:
                return await self._gemini.generate_response(prompt=context.message)
            except Exception as e:
                logger.warning("Gemini unavailable, falling back to Ollama", error=str(e))
                try:
                    return await self._ollama.generate_response(prompt=context.message)
                except Exception as e2:
                    logger.error("Both Gemini and Ollama failed", gemini_error=str(e), ollama_error=str(e2))
                    return "I'm having trouble connecting to AI services right now. Please try again later."

        if category in (RequestCategory.COMPANY_KNOWLEDGE, RequestCategory.DOCUMENT_QUERY):
            return await self._knowledge.execute(context)

        return FEATURE_PLACEHOLDER
