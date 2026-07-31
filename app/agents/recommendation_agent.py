from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.core.logging import logger


class RecommendationAgent(BaseAgent):
    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info("RecommendationAgent executing", category=category.value)
        return "I can provide recommendations. Try asking about what to focus on or what's important today."

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return [RequestCategory.RECOMMENDATION]
