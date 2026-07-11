import time
from typing import Any

from app.orchestrator.enums import IntentType
from app.core.logging import logger
from app.response import templates as tpl


class ResponseFormatter:
    """Converts structured backend data into professional executive responses.

    Each intent is handled by a dedicated ``_format_<intent>`` method.
    If no specific handler exists, ``_format_default`` is used.
    """

    def format(self, intent: IntentType, data: dict[str, Any] | None = None) -> str:
        start = time.monotonic()
        handler = getattr(self, f"_format_{intent.value}", self._format_default)
        result = handler(data or {})
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.debug(
            "Response formatted",
            intent=intent.value,
            template=handler.__name__,
            elapsed_ms=elapsed_ms,
        )
        return result

    # ── Default fallback ──────────────────────────────────────────────────

    def _format_default(self, data: dict[str, Any]) -> str:
        return data.get("message", "Request completed successfully.")

    # ── Projects ──────────────────────────────────────────────────────────

    def _format_create_project(self, data: dict[str, Any]) -> str:
        return tpl.PROJECT_CREATED.format(
            name=data.get("name", "Project"),
            status=data.get("status", "Active"),
        )

    def _format_show_projects(self, data: dict[str, Any]) -> str:
        projects = data.get("projects", [])
        if not projects:
            return "You have no projects at the moment."
        lines = [tpl.PROJECT_LIST_ITEM.format(**p) for p in projects]
        return tpl.PROJECT_LIST_HEADER.format(
            count=len(projects),
            project_list="\n".join(lines),
        )

    def _format_show_project_status(self, data: dict[str, Any]) -> str:
        return tpl.PROJECT_STATUS.format(
            name=data.get("name", data.get("project", "Project")),
            status=data.get("status", data.get("project_status", "Active")),
            progress=data.get("progress", 0),
            deadline=data.get("deadline", "N/A"),
            focus=data.get("focus", "No current focus."),
        )

    def _format_delete_project(self, data: dict[str, Any]) -> str:
        return tpl.PROJECT_DELETED.format(name=data.get("name", "Project"))

    def _format_rename_project(self, data: dict[str, Any]) -> str:
        return tpl.PROJECT_RENAMED.format(name=data.get("name", "Project"))

    # ── Tasks ─────────────────────────────────────────────────────────────

    def _format_create_task(self, data: dict[str, Any]) -> str:
        return tpl.TASK_CREATED.format(
            priority=data.get("priority", "Normal"),
            due_date=data.get("due_date", "Not set"),
        )

    def _format_assign_task(self, data: dict[str, Any]) -> str:
        return tpl.TASK_ASSIGNED.format(assignee=data.get("assignee", "a team member"))

    def _format_update_task(self, data: dict[str, Any]) -> str:
        return tpl.TASK_UPDATED

    def _format_complete_task(self, data: dict[str, Any]) -> str:
        return tpl.TASK_COMPLETED

    def _format_delete_task(self, data: dict[str, Any]) -> str:
        return tpl.TASK_DELETED.format(name=data.get("name", "Task"))

    def _format_change_deadline(self, data: dict[str, Any]) -> str:
        return tpl.TASK_DEADLINE_CHANGED.format(due_date=data.get("due_date", "updated"))

    def _format_change_priority(self, data: dict[str, Any]) -> str:
        return tpl.TASK_PRIORITY_CHANGED.format(priority=data.get("priority", "updated"))

    def _format_show_tasks(self, data: dict[str, Any]) -> str:
        tasks = data.get("tasks", [])
        if not tasks:
            return "You have no tasks at the moment."
        lines = [tpl.TASKS_LIST_ITEM.format(**t) for t in tasks]
        return tpl.TASKS_LIST_HEADER.format(
            count=len(tasks),
            task_list="\n".join(lines),
        )

    def _format_show_overdue(self, data: dict[str, Any]) -> str:
        tasks = data.get("tasks", [])
        if not tasks:
            return "You have no overdue tasks. Well done!"
        lines = [tpl.TASKS_LIST_ITEM.format(**t) for t in tasks]
        return tpl.OVERDUE_HEADER.format(
            count=len(tasks),
            task_list="\n".join(lines),
        )

    # ── Planner ───────────────────────────────────────────────────────────

    def _format_add_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_SCHEDULED.format(
            date=data.get("date", "Today"),
            time=data.get("time", "TBD"),
        )

    def _format_cancel_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_CANCELLED

    def _format_reschedule_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_RESCHEDULED

    def _format_today_schedule(self, data: dict[str, Any]) -> str:
        events = data.get("events", [])
        meetings = [e for e in events if "meeting" in e.get("title", "").lower()]
        deadlines = [e for e in events if "deadline" in e.get("title", "").lower()]
        reminders = [e for e in events if "reminder" in e.get("title", "").lower()]
        return tpl.TODAY_SCHEDULE.format(
            meeting_count=len(meetings) or len(events),
            deadline_count=len(deadlines) or 0,
            reminder_count=len(reminders) or 0,
        )

    def _format_week_schedule(self, data: dict[str, Any]) -> str:
        events = data.get("events", [])
        if not events:
            return "No events scheduled for this week."
        mapped = []
        for e in events:
            item = dict(e)
            if "time" not in item:
                item["time"] = item.pop("start_time", item.pop("start", "TBD"))
            if "end" not in item and "end_time" in item:
                item["end"] = item.pop("end_time")
            mapped.append(item)
        lines = [tpl.EVENTS_LIST_ITEM.format(**e) for e in mapped]
        return tpl.WEEK_SCHEDULE.format(
            count=len(events),
            event_list="\n".join(lines),
        )

    def _format_add_reminder(self, data: dict[str, Any]) -> str:
        return tpl.REMINDER_SET

    # ── Notifications ─────────────────────────────────────────────────────

    def _format_show_notifications(self, data: dict[str, Any]) -> str:
        notifications = data.get("notifications", [])
        if not notifications:
            return "You have no new notifications."
        lines = [tpl.NOTIFICATION_ITEM.format(**n) for n in notifications]
        return tpl.NOTIFICATIONS_HEADER.format(
            count=len(notifications),
            notification_list="\n".join(lines),
        )

    def _format_create_notification(self, data: dict[str, Any]) -> str:
        return tpl.NOTIFICATION_CREATED

    def _format_mark_as_read(self, data: dict[str, Any]) -> str:
        return tpl.NOTIFICATION_MARKED_READ

    # ── Dashboard ─────────────────────────────────────────────────────────

    def _format_focus_today(self, data: dict[str, Any]) -> str:
        return tpl.FOCUS_TODAY.format(
            focus=data.get("focus", "No focus available."),
        )

    def _format_executive_summary(self, data: dict[str, Any]) -> str:
        now = time.localtime()
        hour = now.tm_hour
        greeting = "Morning" if hour < 12 else "Afternoon" if hour < 18 else "Evening"
        return tpl.EXECUTIVE_SUMMARY.format(
            greeting=greeting,
            project_count=data.get("project_count", data.get("active_projects", 0)),
            task_count=data.get("task_count", data.get("pending_tasks", 0)),
            overdue_count=data.get("overdue_count", data.get("overdue_tasks", 0)),
            meeting_count=data.get("meeting_count", data.get("meetings_today", 0)),
            risk_level=data.get("risk_level", data.get("business_risk", "Low")),
            top_priority=data.get("top_priority", data.get("focus", "No priority set.")),
        )

    def _format_today_priorities(self, data: dict[str, Any]) -> str:
        priorities = data.get("priorities", [])
        if not priorities:
            return "No priorities set for today."
        lines = [tpl.PRIORITY_ITEM.format(**p) for p in priorities]
        return tpl.TODAY_PRIORITIES.format(priority_list="\n".join(lines))

    def _format_business_risk(self, data: dict[str, Any]) -> str:
        risks = data.get("risks", [])
        if not risks:
            return "No business risks identified."
        lines = [tpl.RISK_ITEM.format(**r) for r in risks]
        return tpl.BUSINESS_RISK.format(risk_list="\n".join(lines))
