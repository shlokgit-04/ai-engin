from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.pipeline import ExecutionPipeline
from app.core.logging import logger


class MeetingAgent(BaseAgent):
    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        self._pipeline = pipeline

    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info("MeetingAgent executing", category=category.value)
        if self._pipeline:
            return await self._pipeline.execute(category, context)
        return "I can help with meetings. Try: 'show meetings', 'create meeting', 'upload MOM', or 'analyze MOM'."

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return [RequestCategory.MEETING]
