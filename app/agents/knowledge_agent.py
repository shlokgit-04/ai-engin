from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.pipeline import ExecutionPipeline
from app.services.knowledge_search import KnowledgeSearchService
from app.core.logging import logger


class KnowledgeAgent(BaseAgent):
    def __init__(self, pipeline: ExecutionPipeline) -> None:
        self._pipeline = pipeline
        self._knowledge_service = KnowledgeSearchService()

    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info(
            "KnowledgeAgent executing",
            category=category.value,
            message_length=len(context.message),
        )

        if category in (RequestCategory.COMPANY_KNOWLEDGE, RequestCategory.DOCUMENT_QUERY):
            search_results = await self._knowledge_service.search(
                query=context.message,
                top_k=10,
            )
            rag_context = self._knowledge_service.build_rag_context(search_results)

            if rag_context:
                augmented_message = f"{rag_context}\n\nUSER QUESTION: {context.message}"
                rag_context_obj = ExecutionContext(
                    message=augmented_message,
                    metadata={"rag_sources": [r.get("source_title", "") for r in search_results[:5]]},
                )
                return await self._pipeline.execute(category, rag_context_obj)

        if category == RequestCategory.GENERAL_CHAT:
            search_results = await self._knowledge_service.search(
                query=context.message,
                top_k=5,
            )
            if search_results:
                rag_context = self._knowledge_service.build_rag_context(search_results)
                augmented_message = f"{rag_context}\n\nUSER QUESTION: {context.message}"
                rag_context_obj = ExecutionContext(message=augmented_message)
                return await self._pipeline.execute(category, rag_context_obj)

        return await self._pipeline.execute(category, context)

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return [
            RequestCategory.GENERAL_CHAT,
            RequestCategory.COMPANY_KNOWLEDGE,
            RequestCategory.DOCUMENT_QUERY,
            RequestCategory.UNKNOWN,
        ]
