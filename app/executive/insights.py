import time
from typing import Any

from app.core.logging import logger


class BusinessInsights:
    def generate(
        self,
        tasks: list[dict[str, Any]],
        overdue_tasks: list[dict[str, Any]],
        events: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        dashboard_data: dict[str, Any] | None = None,
    ) -> list[str]:
        start = time.monotonic()

        insights = self._evaluate(tasks, overdue_tasks, events, notifications, dashboard_data)

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.debug("Insights generated", count=len(insights), elapsed_ms=elapsed_ms)
        return insights

    def _evaluate(
        self,
        tasks: list[dict[str, Any]],
        overdue_tasks: list[dict[str, Any]],
        events: list[dict[str, Any]],
        notifications: list[dict[str, Any]],
        dashboard_data: dict[str, Any] | None,
    ) -> list[str]:
        insights: list[str] = []

        if overdue_tasks:
            count = len(overdue_tasks)
            if count == 1:
                insights.append("You have 1 overdue task that needs attention.")
            else:
                insights.append(f"You have {count} overdue tasks.")

        if not events:
            insights.append("No meetings scheduled today.")

        if dashboard_data:
            risks = dashboard_data.get("risks")
            if risks and len(risks) > 0:
                high_risks = [r for r in risks if isinstance(r, dict) and r.get("level", "").lower() == "high"]
                if high_risks:
                    insights.append(f"{len(high_risks)} high-risk item(s) require attention.")

        total_tasks = len(tasks)
        if total_tasks > 0:
            pending = sum(1 for t in tasks if t.get("status", "").lower() == "pending")
            if pending <= 3 and not overdue_tasks:
                insights.append("Today's workload appears manageable.")
            elif pending > 8:
                insights.append(f"You have {pending} pending tasks — consider delegating or reprioritising.")

        if notifications:
            unread = sum(1 for n in notifications if not n.get("read", True))
            if unread > 5:
                insights.append(f"You have {unread} unread notifications.")

        return insights
