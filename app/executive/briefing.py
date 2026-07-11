import time
from typing import Any

from app.core.logging import logger
from app.executive.priorities import PriorityEngine
from app.executive.insights import BusinessInsights
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import (
    DashboardResponse,
    TaskListResponse,
    EventListResponse,
    NotificationListResponse,
)


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

    async def generate_briefing(self) -> str:
        start = time.monotonic()

        dashboard_data = await self._fetch_dashboard()
        tasks_data = await self._fetch_tasks()
        overdue_data = await self._fetch_overdue()
        events_data = await self._fetch_events()
        notifications_data = await self._fetch_notifications()

        elapsed_api_ms = round((time.monotonic() - start) * 1000, 2)

        tasks = tasks_data.get("tasks", [])
        overdue = overdue_data.get("tasks", [])
        events = events_data.get("events", [])
        notifications = notifications_data.get("notifications", [])
        dashboard = dashboard_data.get("data") or dashboard_data

        pending_count = len(tasks)
        overdue_count = len(overdue)
        meeting_count = len(events)

        unread = sum(1 for n in notifications if not n.get("read", True))
        risk_level = "Low"
        if isinstance(dashboard, dict):
            risks = dashboard.get("risks")
            if risks:
                high = [r for r in risks if isinstance(r, dict) and r.get("level", "").lower() == "high"]
                medium = [r for r in risks if isinstance(r, dict) and r.get("level", "").lower() == "medium"]
                if high:
                    risk_level = "High"
                elif medium:
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

    async def _fetch_dashboard(self) -> dict[str, Any]:
        data = await self._client.get("/dashboard")
        resp = DashboardResponse(**data)
        return resp.model_dump()

    async def _fetch_tasks(self) -> dict[str, Any]:
        data = await self._client.get("/tasks")
        resp = TaskListResponse(**data)
        return {"tasks": [t.model_dump() for t in resp.tasks]}

    async def _fetch_overdue(self) -> dict[str, Any]:
        data = await self._client.get("/tasks/overdue")
        resp = TaskListResponse(**data)
        return {"tasks": [t.model_dump() for t in resp.tasks]}

    async def _fetch_events(self) -> dict[str, Any]:
        data = await self._client.get("/planner/today")
        resp = EventListResponse(**data)
        return {"events": [e.model_dump() for e in resp.events]}

    async def _fetch_notifications(self) -> dict[str, Any]:
        data = await self._client.get("/notifications")
        resp = NotificationListResponse(**data)
        return {"notifications": [n.model_dump() for n in resp.notifications]}
