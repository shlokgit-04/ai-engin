from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.executive.briefing import ExecutiveBriefingService
from app.core.logging import logger


class ExecutiveTool(BaseTool):
    def __init__(
        self,
        briefing_service: ExecutiveBriefingService | None = None,
    ) -> None:
        self._briefing_service = briefing_service or ExecutiveBriefingService()

    async def execute(self, context: ExecutionContext, intent: IntentType) -> str:
        try:
            if intent == IntentType.DAILY_BRIEFING:
                return await self._briefing_service.generate_briefing(auth_token=context.auth_token)
            return "I'm not sure how to handle that request."
        except Exception:
            logger.exception("ExecutiveTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    def name(self) -> str:
        return "ExecutiveTool"

    def description(self) -> str:
        return "Executive briefing — combine dashboard, tasks, schedule, and notifications."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return ["daily_briefing"]
