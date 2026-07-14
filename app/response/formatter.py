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
        title = data.get("title", "Meeting")
        date = data.get("date", "Not scheduled")
        time_str = data.get("time", "TBD")
        parts = [f'"{title}" created successfully.']
        if date and date.lower() not in ("not scheduled", "none"):
            parts.append(f"📅 {date}")
        if time_str and time_str.lower() not in ("not scheduled", "none", "tbd"):
            parts.append(f"🕐 {time_str}")
        return "\n".join(parts)

    def _format_cancel_meeting(self, data: dict[str, Any]) -> str:
        title = data.get("title", "the meeting")
        return f'"{title}" has been deleted successfully.'

    def _format_reschedule_meeting(self, data: dict[str, Any]) -> str:
        title = data.get("title", "The meeting")
        parts = [f'"{title}" has been rescheduled.']
        date = data.get("date")
        time_str = data.get("time")
        if date:
            parts.append(f"📅 {date}")
        if time_str:
            parts.append(f"🕐 {time_str}")
        return "\n".join(parts)

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

    def _format_upload_mom(self, data: dict[str, Any]) -> str:
        return tpl.MOM_UPLOADED.format(meeting_id=data.get("meeting_id", ""))

    def _format_extract_tasks_from_mom(self, data: dict[str, Any]) -> str:
        tasks = data.get("tasks", [])
        summary = data.get("mom_summary", "")
        if tasks:
            lines = [f"  • {t.get('title', t)}" for t in tasks]
            return f"Tasks extracted from meeting #{data.get('meeting_id', '')}:\n\n" + "\n".join(lines)
        return tpl.TASKS_EXTRACTED.format(
            meeting_id=data.get("meeting_id", ""),
            meeting_summary=summary or "No summary available.",
        )

    def _format_accept_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_INVITATION_ACCEPTED

    def _format_decline_meeting(self, data: dict[str, Any]) -> str:
        return tpl.MEETING_INVITATION_DECLINED

    # ── Meeting Intelligence (new) ────────────────────────────────────────

    def _format_show_meetings(self, data: dict[str, Any]) -> str:
        events = data.get("events", [])
        if not events:
            return "You have no meetings at the moment."
        lines = []
        for e in events:
            title = e.get("title", "Untitled")
            date = e.get("date") or ""
            time_str = e.get("time") or ""
            parts = [f"  • {title}"]
            if date and date.lower() not in ("not scheduled", "none", ""):
                parts.append(f"    📅 {date}")
            if time_str and time_str.lower() not in ("not scheduled", "none", "tbd", ""):
                parts.append(f"    🕐 {time_str}")
            lines.append("\n".join(parts))
        return tpl.MEETINGS_LIST_HEADER.format(count=len(events), meeting_list="\n".join(lines))

    def _format_today_meetings(self, data: dict[str, Any]) -> str:
        events = data.get("events", [])
        if not events:
            return "No meetings scheduled for today."
        lines = []
        for e in events:
            title = e.get("title", "Untitled")
            time_str = e.get("time") or ""
            parts = [f"  • {title}"]
            if time_str and time_str.lower() not in ("not scheduled", "none", "tbd", ""):
                parts.append(f"    🕐 {time_str}")
            lines.append("\n".join(parts))
        return tpl.MEETINGS_LIST_HEADER.format(count=len(events), meeting_list="\n".join(lines))

    def _format_upcoming_meetings(self, data: dict[str, Any]) -> str:
        events = data.get("events", [])
        if not events:
            return "No upcoming meetings."
        lines = []
        for e in events:
            title = e.get("title", "Untitled")
            date = e.get("date") or ""
            time_str = e.get("time") or ""
            parts = [f"  • {title}"]
            if date and date.lower() not in ("not scheduled", "none", ""):
                parts.append(f"    📅 {date}")
            if time_str and time_str.lower() not in ("not scheduled", "none", "tbd", ""):
                parts.append(f"    🕐 {time_str}")
            lines.append("\n".join(parts))
        return tpl.MEETINGS_LIST_HEADER.format(count=len(events), meeting_list="\n".join(lines))

    def _format_show_meeting_timeline(self, data: dict[str, Any]) -> str:
        timeline = data.get("timeline", [])
        if not timeline:
            return f"No timeline events recorded for meeting #{data.get('meeting_id', '')}."
        lines = []
        for t in timeline:
            user = t.get("user_name") or t.get("user", "System")
            desc = t.get("description", t.get("action", ""))
            lines.append(f"  • {desc} ({user})")
        return tpl.MEETING_TIMELINE_HEADER.format(
            meeting_id=data.get("meeting_id", ""),
            count=len(timeline),
            timeline_list="\n".join(lines),
        )

    def _format_analyze_mom(self, data: dict[str, Any]) -> str:
        def _parse_json_field(val):
            if isinstance(val, str):
                try:
                    import json as _json
                    return _json.loads(val)
                except Exception:
                    return []
            if isinstance(val, list):
                return val
            return []

        def _parse_json_str(val):
            if isinstance(val, str):
                try:
                    import json as _json
                    return _json.loads(val)
                except Exception:
                    return val
            return val

        decisions = _parse_json_field(data.get("decisions", []))
        risks = _parse_json_field(data.get("risks", []))
        followups = _parse_json_field(data.get("followups", []))
        blockers = _parse_json_field(data.get("blockers", []))
        exec_summary = _parse_json_str(data.get("executive_summary", "")) or "No executive summary available."

        parts = [
            f"Meeting #{data.get('meeting_id', '')} MOM Analysis\n",
            f"Executive Summary:\n{exec_summary}\n",
        ]
        if decisions:
            parts.append("Decisions:\n" + "\n".join(f"  • {d}" for d in decisions))
        if risks:
            parts.append("Risks:\n" + "\n".join(f"  • {r}" for r in risks))
        if followups:
            parts.append("Follow-ups:\n" + "\n".join(f"  • {f}" for f in followups))
        if blockers:
            parts.append("Blockers:\n" + "\n".join(f"  • {b}" for b in blockers))
        return "\n\n".join(parts)

    def _format_show_extracted_tasks(self, data: dict[str, Any]) -> str:
        tasks = data.get("tasks", [])
        if not tasks:
            return f"No extracted tasks for meeting #{data.get('meeting_id', '')}."
        lines = []
        for t in tasks:
            lines.append(tpl.EXTRACTED_TASKS_ITEM.format(
                status=t.get("status", "pending"),
                title=t.get("title", "Untitled"),
                confidence=int(t.get("confidence", 0)),
            ))
        return tpl.EXTRACTED_TASKS_LIST_HEADER.format(
            meeting_id=data.get("meeting_id", ""),
            count=len(tasks),
            task_list="\n".join(lines),
        )

    def _format_approve_extracted_tasks(self, data: dict[str, Any]) -> str:
        return tpl.EXTRACTED_TASKS_APPROVED.format(
            count=data.get("approved_count", 0),
            meeting_id=data.get("meeting_id", ""),
        )

    def _format_reject_extracted_tasks(self, data: dict[str, Any]) -> str:
        return tpl.EXTRACTED_TASKS_REJECTED.format(
            count=data.get("rejected_count", 0),
            meeting_id=data.get("meeting_id", ""),
        )

    def _format_who_accepted(self, data: dict[str, Any]) -> str:
        accepted = data.get("accepted", [])
        if not accepted:
            return f"No one has accepted meeting #{data.get('meeting_id', '')} yet."
        lines = "\n".join(f"  • {name}" for name in accepted)
        return tpl.MEETING_ACCEPTED_LIST.format(
            meeting_id=data.get("meeting_id", ""),
            count=len(accepted),
            names_list=lines,
        )

    def _format_who_declined(self, data: dict[str, Any]) -> str:
        declined = data.get("declined", [])
        if not declined:
            return f"No one has declined meeting #{data.get('meeting_id', '')}."
        lines = "\n".join(f"  • {name}" for name in declined)
        return tpl.MEETING_DECLINED_LIST.format(
            meeting_id=data.get("meeting_id", ""),
            count=len(declined),
            names_list=lines,
        )

    def _format_meeting_decisions(self, data: dict[str, Any]) -> str:
        items = data.get("decisions", [])
        if isinstance(items, str):
            try:
                import json as _json
                items = _json.loads(items)
            except Exception:
                items = [items] if items else []
        if not items:
            return f"No decisions recorded for meeting #{data.get('meeting_id', '')}."
        lines = "\n".join(f"  • {item}" for item in items)
        return tpl.MEETING_DECISIONS_HEADER.format(
            meeting_id=data.get("meeting_id", ""),
            items_list=lines,
        )

    def _format_meeting_risks(self, data: dict[str, Any]) -> str:
        items = data.get("risks", [])
        if isinstance(items, str):
            try:
                import json as _json
                items = _json.loads(items)
            except Exception:
                items = [items] if items else []
        if not items:
            return f"No risks identified for meeting #{data.get('meeting_id', '')}."
        lines = "\n".join(f"  • {item}" for item in items)
        return tpl.MEETING_RISKS_HEADER.format(
            meeting_id=data.get("meeting_id", ""),
            items_list=lines,
        )

    def _format_meeting_followups(self, data: dict[str, Any]) -> str:
        items = data.get("followups", [])
        if isinstance(items, str):
            try:
                import json as _json
                items = _json.loads(items)
            except Exception:
                items = [items] if items else []
        if not items:
            return f"No follow-up items for meeting #{data.get('meeting_id', '')}."
        lines = "\n".join(f"  • {item}" for item in items)
        return tpl.MEETING_FOLLOWUPS_HEADER.format(
            meeting_id=data.get("meeting_id", ""),
            items_list=lines,
        )

    def _format_meeting_blockers(self, data: dict[str, Any]) -> str:
        items = data.get("blockers", [])
        if isinstance(items, str):
            try:
                import json as _json
                items = _json.loads(items)
            except Exception:
                items = [items] if items else []
        if not items:
            return f"No blockers identified for meeting #{data.get('meeting_id', '')}."
        lines = "\n".join(f"  • {item}" for item in items)
        return tpl.MEETING_BLOCKERS_HEADER.format(
            meeting_id=data.get("meeting_id", ""),
            items_list=lines,
        )

    def _format_rename_meeting(self, data: dict[str, Any]) -> str:
        title = data.get("title", "the meeting")
        return f'Meeting renamed to "{title}" successfully.'

    def _format_add_participant(self, data: dict[str, Any]) -> str:
        participant = data.get("participant", "the user")
        action = data.get("action", "added")
        return f"{participant} has been {action} to the meeting."

    def _format_remove_participant(self, data: dict[str, Any]) -> str:
        participant = data.get("participant", "the user")
        action = data.get("action", "removed")
        return f"{participant} has been {action} from the meeting."

    def _format_show_meeting_detail(self, data: dict[str, Any]) -> str:
        title = data.get("title", "Untitled Meeting")
        parts = [f"📋 {title}"]

        date_val = data.get("date")
        time_val = data.get("start_time")
        end_val = data.get("end_time")
        if date_val:
            parts.append(f"📅 {date_val}")
        elif time_val:
            parts.append(f"🕐 {time_val}")
        else:
            parts.append("📅 Not scheduled")

        location = data.get("location")
        if location:
            parts.append(f"📍 {location}")

        link = data.get("meeting_link")
        if link:
            parts.append(f"🔗 {link}")

        agenda = data.get("agenda")
        if agenda:
            parts.append(f"\nAgenda:\n{agenda}")

        owner = data.get("owner_name")
        if owner:
            parts.append(f"\nHost: {owner}")

        participants = data.get("participants", [])
        if participants:
            accepted = sum(1 for p in participants if p.get("status") == "accepted")
            declined = sum(1 for p in participants if p.get("status") == "declined")
            pending = sum(1 for p in participants if p.get("status") in ("pending", None))
            names = [p.get("user_name", "Unknown") for p in participants]
            parts.append(f"\nParticipants ({len(participants)}):\n" + "\n".join(f"  • {n}" for n in names))
            status_parts = []
            if accepted:
                status_parts.append(f"{accepted} accepted")
            if declined:
                status_parts.append(f"{declined} declined")
            if pending:
                status_parts.append(f"{pending} pending")
            if status_parts:
                parts.append("Status: " + ", ".join(status_parts))

        mom = data.get("mom_summary")
        if mom:
            parts.append("\n📝 MOM: Uploaded")
        else:
            parts.append("\n📝 MOM: Not uploaded")

        return "\n".join(parts)

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
