from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.pipeline import ExecutionPipeline, FEATURE_PLACEHOLDER
from app.core.logging import logger


class KnowledgeAgent(BaseAgent):
    def __init__(self, pipeline: ExecutionPipeline) -> None:
        self._pipeline = pipeline

    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info(
            "KnowledgeAgent executing",
            category=category.value,
            message_length=len(context.message),
        )
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
