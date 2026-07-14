import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.exceptions import (
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.core.logging import logger


_ERROR_MAP: dict[type, str] = {
    BackendConnectionError: "I couldn't reach the backend service.",
    BackendTimeoutError: "The backend took too long to respond.",
    BackendServerError: "The backend is currently unavailable.",
}


class DashboardTool(BaseTool):
    def __init__(
        self,
        client: BackendClient | None = None,
        formatter: ResponseFormatter | None = None,
    ) -> None:
        self._client = client or BackendClient()
        self._formatter = formatter or ResponseFormatter()

    async def execute(self, context: ExecutionContext, intent: IntentType) -> str:
        try:
            return await self._route(context, intent)
        except tuple(_ERROR_MAP) as exc:
            msg = _ERROR_MAP.get(type(exc), "An unexpected error occurred.")
            logger.warning("DashboardTool error", intent=intent.value, error=str(exc))
            return msg
        except Exception:
            logger.exception("DashboardTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()
        token = context.auth_token
        data = await self._client.get("/api/v1/dashboard/summary", auth_token=token)

        if intent == IntentType.FOCUS_TODAY:
            focus = f"{data.get('todayTasks', 0)} tasks today, {data.get('overdueTasks', 0)} overdue, {data.get('todayMeetings', 0)} meetings"
            if data.get('pendingInvitations', 0):
                focus += f", {data.get('pendingInvitations', 0)} pending invitation(s)"
            if data.get('meetingsNeedingMOM', 0):
                focus += f", {data.get('meetingsNeedingMOM', 0)} meeting(s) need MOM"
            if data.get('pendingApprovals', 0):
                focus += f", {data.get('pendingApprovals', 0)} task(s) pending approval"
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /api/v1/dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"focus": focus})

        if intent == IntentType.EXECUTIVE_SUMMARY:
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /api/v1/dashboard/summary", elapsed_ms=elapsed)
            pending = data.get('pendingInvitations', 0)
            top_priority = f"{data.get('highPriorityTasks', 0)} high priority tasks"
            if pending:
                top_priority += f", {pending} pending meeting invitation(s)"
            if data.get('pendingApprovals', 0):
                top_priority += f", {data.get('pendingApprovals', 0)} extracted task(s) to review"
            return self._formatter.format(intent, {
                "project_count": data.get("activeProjects", 0),
                "task_count": data.get("todayTasks", 0),
                "overdue_count": data.get("overdueTasks", 0),
                "meeting_count": data.get("todayMeetings", 0),
                "risk_level": "Low",
                "top_priority": top_priority,
            })

        if intent == IntentType.TODAY_PRIORITIES:
            priorities = [{"title": f"{data.get('highPriorityTasks', 0)} high priority tasks"}, {"title": f"{data.get('overdueTasks', 0)} overdue tasks"}]
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /api/v1/dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"priorities": priorities})

        if intent == IntentType.BUSINESS_RISK:
            overdue = data.get("overdueTasks", 0)
            risks = []
            if overdue > 0:
                risks.append({"level": "Medium", "description": f"{overdue} overdue task(s) need attention"})
            if not risks:
                risks = [{"level": "Low", "description": "No significant risks identified"}]
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /api/v1/dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"risks": risks})

        return "I'm not sure how to handle that request."

    def name(self) -> str:
        return "DashboardTool"

    def description(self) -> str:
        return "Executive dashboard — daily focus, summary, priorities, risk assessment."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "focus_today",
            "executive_summary",
            "today_priorities",
            "business_risk",
        ]
