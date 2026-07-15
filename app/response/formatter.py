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

    # ── Meeting Intelligence ──────────────────────────────────────────────

    def _format_show_meetings(self, data: dict[str, Any]) -> str:
        meetings = data.get("meetings", [])
        if not meetings:
            return "You have no meetings at the moment."
        lines = [tpl.MEETING_LIST_ITEM.format(**m) for m in meetings]
        return tpl.MEETING_LIST_HEADER.format(
            count=len(meetings),
            meeting_list="\n".join(lines),
        )

    def _format_today_meetings(self, data: dict[str, Any]) -> str:
        meetings = data.get("meetings", [])
        if not meetings:
            return "You have no meetings scheduled for today."
        lines = [tpl.MEETING_LIST_ITEM.format(**m) for m in meetings]
        return tpl.MEETING_LIST_HEADER.format(
            count=len(meetings),
            meeting_list="\n".join(lines),
        )

    def _format_upcoming_meetings(self, data: dict[str, Any]) -> str:
        meetings = data.get("meetings", [])
        if not meetings:
            return "No upcoming meetings."
        lines = [tpl.MEETING_LIST_ITEM.format(**m) for m in meetings]
        return tpl.MEETING_LIST_HEADER.format(
            count=len(meetings),
            meeting_list="\n".join(lines),
        )

    def _format_show_meeting_detail(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_DETAIL.format(
            title=data.get("title", "Meeting"),
            id=data.get("id", "?"),
            date=data.get("date", "Not set"),
            time=data.get("start_time", "Not set"),
            location=data.get("location", "Not set"),
            agenda=data.get("agenda", "Not set"),
            participants=data.get("participants", "None"),
            mom=data.get("mom_summary", "Not uploaded"),
        )

    def _format_rename_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_RENAMED.format(
            id=data.get("id", "?"),
            new_name=data.get("new_name", "Meeting"),
        )

    def _format_add_participant(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_PARTICIPANT_ADDED.format(
            user_name=data.get("user_name", "Participant"),
            id=data.get("id", "?"),
        )

    def _format_remove_participant(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_PARTICIPANT_REMOVED.format(
            user_name=data.get("user_name", "Participant"),
            id=data.get("id", "?"),
        )

    def _format_accept_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_ACCEPTED.format(id=data.get("id", "?"))

    def _format_decline_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_DECLINED.format(id=data.get("id", "?"))

    def _format_who_accepted(self, data: dict[str, Any]) -> str:
        names = data.get("names", "Nobody")
        return tpl.MEETING_ACCEPTED_BY.format(
            status="Accepted",
            id=data.get("id", "?"),
            names=names,
        )

    def _format_who_declined(self, data: dict[str, Any]) -> str:
        names = data.get("names", "Nobody")
        return tpl.MEETING_ACCEPTED_BY.format(
            status="Declined",
            id=data.get("id", "?"),
            names=names,
        )

    def _format_upload_mom(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_MOM_UPLOADED.format(id=data.get("id", "?"))

    def _format_analyze_mom(self, data: dict[str, Any]) -> str:
        analysis_parts = []
        for key in ("mom_executive_summary", "mom_decisions", "mom_risks", "mom_followups", "mom_blockers"):
            value = data.get(key)
            if value:
                label = key.replace("mom_", "").replace("_", " ").title()
                analysis_parts.append(f"**{label}:** {value}")
        tasks = data.get("extracted_tasks", [])
        if tasks:
            analysis_parts.append(f"**{len(tasks)} task(s) extracted.**")
        return tpl.MEETING_MOM_ANALYSIS.format(
            id=data.get("id", "?"),
            analysis="\n".join(analysis_parts) if analysis_parts else "No analysis data available.",
        )

    def _format_extract_tasks_from_mom(self, data: dict[str, Any]) -> str:
        return self._format_analyze_mom(data)

    def _format_show_extracted_tasks(self, data: dict[str, Any]) -> str:
        tasks = data.get("tasks", [])
        if not tasks:
            return "No extracted tasks."
        lines = [tpl.MEETING_EXTRACTED_TASK_ITEM.format(**t) for t in tasks]
        return tpl.MEETING_EXTRACTED_TASKS_HEADER.format(
            id=data.get("id", "?"),
            task_list="\n".join(lines),
        )

    def _format_approve_extracted_tasks(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_TASKS_APPROVED.format(id=data.get("id", "?"))

    def _format_reject_extracted_tasks(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_TASKS_REJECTED.format(id=data.get("id", "?"))

    def _format_show_meeting_timeline(self, data: dict[str, Any]) -> str:
        events = data.get("events", [])
        if not events:
            return "No timeline events."
        lines = [tpl.MEETING_TIMELINE_ITEM.format(**e) for e in events]
        return tpl.MEETING_TIMELINE_HEADER.format(
            id=data.get("id", "?"),
            events="\n".join(lines),
        )

    def _format_show_meeting_decisions(self, data: dict[str, Any]) -> str:
        value = data.get("value", "No decisions recorded.")
        return tpl.MEETING_MOM_FIELD.format(field="Decisions", id=data.get("id", "?"), value=value)

    def _format_show_meeting_risks(self, data: dict[str, Any]) -> str:
        value = data.get("value", "No risks recorded.")
        return tpl.MEETING_MOM_FIELD.format(field="Risks", id=data.get("id", "?"), value=value)

    def _format_show_meeting_followups(self, data: dict[str, Any]) -> str:
        value = data.get("value", "No follow-ups recorded.")
        return tpl.MEETING_MOM_FIELD.format(field="Follow-ups", id=data.get("id", "?"), value=value)

    def _format_show_meeting_blockers(self, data: dict[str, Any]) -> str:
        value = data.get("value", "No blockers recorded.")
        return tpl.MEETING_MOM_FIELD.format(field="Blockers", id=data.get("id", "?"), value=value)

    # ── Notifications ─────────────────────────────────────────────────────

    def _format_show_notifications(self, data: dict[str, Any]) -> str:
        notifications = data.get("notifications", [])
        if not notifications:
            return "You have no new notifications."
        lines = []
        for n in notifications:
            title = n.get("title") or n.get("text") or ""
            msg = n.get("message") or ""
            text = f"{title}: {msg}" if msg else title
            lines.append(f"  • {text}")
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
