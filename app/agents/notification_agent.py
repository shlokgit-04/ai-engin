from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.core.logging import logger


class NotificationAgent(BaseAgent):
    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info("NotificationAgent executing", category=category.value)
        return "I can help you manage notifications. Try saying: show my notifications or mark as read."

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return []
