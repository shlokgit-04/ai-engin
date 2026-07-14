import time
from typing import Any

from app.core.logging import logger
from app.executive.priorities import PriorityEngine
from app.executive.insights import BusinessInsights
from app.integrations.backend.client import BackendClient


BRIEFING_TEMPLATE = (
    "Good {greeting}.\n\n"
    "Today's Executive Brief\n\n"
    "  • Tasks: {pending_count} Pending, {overdue_count} Overdue\n"
    "  • Meetings: {meeting_count} Scheduled Today\n"
    "  • Notifications: {unread_notification_count} Unread\n\n"
    "Highest Priority\n"
    "{highest_priority}\n\n"
    "Business Risk\n"
    "{risk_level}\n\n"
    "Insights\n"
    "{insights_text}"
)


class ExecutiveBriefingService:
    def __init__(
        self,
        client: BackendClient | None = None,
        priority_engine: PriorityEngine | None = None,
        insights_engine: BusinessInsights | None = None,
    ) -> None:
        self._client = client or BackendClient()
        self._priority_engine = priority_engine or PriorityEngine()
        self._insights_engine = insights_engine or BusinessInsights()

    async def generate_briefing(self, auth_token: str | None = None) -> str:
        start = time.monotonic()

        dashboard_data = await self._fetch_dashboard(auth_token)
        tasks_data = await self._fetch_tasks(auth_token)
        overdue_data = await self._fetch_overdue(auth_token)
        events_data = await self._fetch_events(auth_token)
        notifications_data = await self._fetch_notifications(auth_token)

        elapsed_api_ms = round((time.monotonic() - start) * 1000, 2)

        tasks = tasks_data if isinstance(tasks_data, list) else []
        overdue = overdue_data if isinstance(overdue_data, list) else []
        events = events_data if isinstance(events_data, list) else []
        notifications = notifications_data if isinstance(notifications_data, list) else []
        dashboard = dashboard_data if isinstance(dashboard_data, dict) else {}

        pending_count = len(tasks)
        overdue_count = len(overdue)
        meeting_count = len(events)

        unread = sum(1 for n in notifications if not n.get("is_read", True))
        risk_level = "Low"
        if overdue_count > 3:
            risk_level = "High"
        elif overdue_count > 0:
            risk_level = "Medium"

        highest_priority = self._priority_engine.determine_priority(tasks, overdue, events, dashboard)
        insights = self._insights_engine.generate(tasks, overdue, events, notifications, dashboard)

        now = time.localtime()
        hour = now.tm_hour
        greeting = "Morning" if hour < 12 else "Afternoon" if hour < 18 else "Evening"

        insights_text = "\n".join(f"  • {i}" for i in insights) if insights else "  • No specific insights."

        result = BRIEFING_TEMPLATE.format(
            greeting=greeting,
            pending_count=pending_count,
            overdue_count=overdue_count,
            meeting_count=meeting_count,
            unread_notification_count=unread,
            highest_priority=highest_priority,
            risk_level=risk_level,
            insights_text=insights_text,
        )

        elapsed_total_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "Executive briefing generated",
            api_calls=5,
            api_elapsed_ms=elapsed_api_ms,
            total_elapsed_ms=elapsed_total_ms,
            priority=highest_priority,
        )
        return result

    async def _fetch_dashboard(self, auth_token: str | None = None) -> dict[str, Any]:
        return await self._client.get("/api/v1/dashboard/summary", auth_token=auth_token)

    async def _fetch_tasks(self, auth_token: str | None = None) -> list[dict[str, Any]]:
        return await self._client.get("/api/v1/tasks", auth_token=auth_token)

    async def _fetch_overdue(self, auth_token: str | None = None) -> list[dict[str, Any]]:
        return await self._client.get("/api/v1/tasks/overdue", auth_token=auth_token)

    async def _fetch_events(self, auth_token: str | None = None) -> list[dict[str, Any]]:
        return await self._client.get("/api/v1/meetings", params={"filter": "today"}, auth_token=auth_token)

    async def _fetch_notifications(self, auth_token: str | None = None) -> list[dict[str, Any]]:
        return await self._client.get("/api/v1/notifications", auth_token=auth_token)
