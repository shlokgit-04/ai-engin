from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.pipeline import FEATURE_PLACEHOLDER
from app.core.logging import logger


class MeetingAgent(BaseAgent):
    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info("MeetingAgent executing", category=category.value)
        return FEATURE_PLACEHOLDER

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return [RequestCategory.MEETING]
