import time
from typing import Any

from app.core.logging import logger


class PriorityEngine:
    def determine_priority(
        self,
        tasks: list[dict[str, Any]],
        overdue_tasks: list[dict[str, Any]],
        events: list[dict[str, Any]],
        dashboard_data: dict[str, Any] | None = None,
    ) -> str:
        start = time.monotonic()

        priority = self._evaluate(tasks, overdue_tasks, events, dashboard_data)

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.debug("Priority determined", priority=priority, elapsed_ms=elapsed_ms)
        return priority

    def _evaluate(
        self,
        tasks: list[dict[str, Any]],
        overdue_tasks: list[dict[str, Any]],
        events: list[dict[str, Any]],
        dashboard_data: dict[str, Any] | None,
    ) -> str:
        if overdue_tasks:
            titles = [t.get("title", "") for t in overdue_tasks if t.get("title")]
            if titles:
                return f"Complete overdue work: {titles[0]}"
            return "Complete overdue work"

        if events:
            now_hour = time.localtime().tm_hour
            for event in events:
                start_str = event.get("start", "")
                if start_str and ":" in start_str:
                    try:
                        hour = int(start_str.split(":")[0])
                        if 0 <= hour - now_hour < 1:
                            title = event.get("title", "Meeting")
                            return f"Prepare for upcoming meeting: {title}"
                    except (ValueError, IndexError):
                        pass

        top_priority = None
        if dashboard_data:
            priorities = dashboard_data.get("priorities")
            if priorities and len(priorities) > 0:
                top_priority = priorities[0].get("title") if isinstance(priorities[0], dict) else str(priorities[0])
            if not top_priority:
                top_priority = dashboard_data.get("focus")

        if top_priority:
            return top_priority

        if tasks:
            return tasks[0].get("title", "Focus on pending tasks")

        return "No priority items identified."
