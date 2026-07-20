import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import DashboardResponse
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
        data = await self._client.get("/dashboard/summary")
        resp = DashboardResponse(**data)
        d = resp.data

        if intent == IntentType.FOCUS_TODAY:
            if not d:
                return self._formatter.format(intent, {"focus": "No dashboard data available."})
            focus_parts = []
            if d.activeProjects:
                focus_parts.append(f"{d.activeProjects} active project(s)")
            if d.todayTasks:
                focus_parts.append(f"{d.todayTasks} task(s) due today")
            if d.overdueTasks:
                focus_parts.append(f"{d.overdueTasks} overdue task(s)")
            if d.todayMeetings:
                focus_parts.append(f"{d.todayMeetings} meeting(s) today")
            if d.highPriorityTasks:
                focus_parts.append(f"{d.highPriorityTasks} high-priority task(s)")
            focus = ", ".join(focus_parts) if focus_parts else "No urgent items today."
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"focus": focus})

        if intent == IntentType.EXECUTIVE_SUMMARY:
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {
                "active_projects": d.activeProjects if d else 0,
                "completed_projects": d.completedProjects if d else 0,
                "total_tasks": d.totalTasks if d else 0,
                "completed_tasks": d.completedTasks if d else 0,
                "overdue_tasks": d.overdueTasks if d else 0,
                "meetings_today": d.todayMeetings if d else 0,
                "high_priority": d.highPriorityTasks if d else 0,
                "upcoming_deadlines": d.upcomingDeadlines if d else 0,
                "business_risk": "High" if (d and d.overdueTasks > 3) else "Medium" if (d and d.overdueTasks > 0) else "Low",
                "focus": f"{d.activeProjects} active projects, {d.totalTasks - d.completedTasks if d else 0} tasks remaining" if d else "",
            })

        if intent == IntentType.TODAY_PRIORITIES:
            priorities = []
            if d:
                if d.highPriorityTasks:
                    priorities.append({"title": f"{d.highPriorityTasks} high-priority task(s) need attention"})
                if d.overdueTasks:
                    priorities.append({"title": f"{d.overdueTasks} overdue task(s) require immediate action"})
                if d.todayTasks:
                    priorities.append({"title": f"{d.todayTasks} task(s) due today"})
                if d.todayMeetings:
                    priorities.append({"title": f"{d.todayMeetings} meeting(s) scheduled today"})
                if d.pendingApprovals:
                    priorities.append({"title": f"{d.pendingApprovals} extracted task(s) awaiting approval"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"priorities": priorities})

        if intent == IntentType.BUSINESS_RISK:
            risks = []
            if d:
                if d.overdueTasks > 3:
                    risks.append({"level": "High", "description": f"{d.overdueTasks} overdue tasks — project timelines at risk"})
                elif d.overdueTasks > 0:
                    risks.append({"level": "Medium", "description": f"{d.overdueTasks} overdue task(s) need attention"})
                if d.highPriorityTasks > 5:
                    risks.append({"level": "High", "description": f"{d.highPriorityTasks} high-priority tasks — workload concern"})
                if d.meetingsNeedingMOM > 3:
                    risks.append({"level": "Medium", "description": f"{d.meetingsNeedingMOM} meeting(s) missing minutes of meeting"})
                if d.upcomingDeadlines > 5:
                    risks.append({"level": "Medium", "description": f"{d.upcomingDeadlines} tasks due in the next 7 days"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
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
