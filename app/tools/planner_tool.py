import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.exceptions import (
    BackendNotFoundError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.executive.params import (
    extract_event_title, extract_event_id, extract_date, extract_time,
    extract_mom_text, extract_participant_name, extract_new_meeting_name,
)
from app.executive.validation import validate_not_empty
from app.executive.suggestions import get_suggestion
from app.core.logging import logger


_FALLBACK = {
    "add_reminder": "Reminder set successfully.",
}

_ERROR_MAP: dict[type, str] = {
    BackendNotFoundError: "I couldn't find that event.",
    BackendConnectionError: "I couldn't reach the backend service.",
    BackendTimeoutError: "The backend took too long to respond.",
    BackendServerError: "The backend is currently unavailable.",
}


class PlannerTool(BaseTool):
    def __init__(
        self,
        client: BackendClient | None = None,
        formatter: ResponseFormatter | None = None,
    ) -> None:
        self._client = client or BackendClient()
        self._formatter = formatter or ResponseFormatter()

    async def execute(self, context: ExecutionContext, intent: IntentType) -> str:
        if intent.value in _FALLBACK:
            return _FALLBACK[intent.value]
        try:
            return await self._route(context, intent)
        except tuple(_ERROR_MAP) as exc:
            msg = _ERROR_MAP.get(type(exc), "An unexpected error occurred.")
            logger.warning("PlannerTool error", intent=intent.value, error=str(exc))
            return msg
        except Exception:
            logger.exception("PlannerTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()
        token = context.auth_token

        if intent == IntentType.ADD_MEETING:
            title = extract_event_title(context.message, "Meeting")
            valid, err = validate_not_empty(title, "Meeting title")
            if not valid:
                return err
            event_date = extract_date(context.message)
            event_time = extract_time(context.message)
            body = {"title": title}
            if event_date:
                body["date"] = event_date
            if event_time:
                body["start_time"] = event_time
                parts = event_time.split(":")
                hour = int(parts[0])
                end_hour = hour + 1
                body["end_time"] = f"{end_hour:02d}:{parts[1]}" if len(parts) > 1 else f"{end_hour:02d}:00"
            data = await self._client.post("/api/v1/meetings", json_body=body, auth_token=token)
            meeting_id = data.get("id") if isinstance(data, dict) else None
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {
                "title": title,
                "date": event_date or "Not scheduled",
                "time": event_time or "TBD",
                "meeting_id": meeting_id,
            })
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, title=title, date=event_date, time=event_time, endpoint="POST /api/v1/meetings", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.CANCEL_MEETING:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find a meeting to delete. Please specify the meeting name."
            meeting_data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            meeting_title = meeting_data.get("title", "the meeting") if isinstance(meeting_data, dict) else "the meeting"
            await self._client.delete(f"/api/v1/meetings/{eid}", auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"title": meeting_title})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"DELETE /api/v1/meetings/{eid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.RESCHEDULE_MEETING:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find a meeting to reschedule. Please specify the meeting name."
            new_date = extract_date(context.message)
            new_time = extract_time(context.message)
            update_body = {}
            if new_date:
                update_body["date"] = new_date
            if new_time:
                update_body["start_time"] = new_time
            if not update_body:
                return "Please specify a new date or time. For example: 'Reschedule Demo to Friday 4 PM'"
            await self._client.put(f"/api/v1/meetings/{eid}", json_body=update_body, auth_token=token)
            meeting_data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            meeting_title = meeting_data.get("title", "the meeting") if isinstance(meeting_data, dict) else "the meeting"
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"title": meeting_title, "date": new_date, "time": new_time})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, date=new_date, time=new_time, endpoint=f"PUT /api/v1/meetings/{eid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.RENAME_MEETING:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find a meeting to rename. Please specify the meeting name."
            new_name = extract_new_meeting_name(context.message)
            if not new_name:
                return "Please specify the new name. For example: 'Rename meeting Demo to AI Demo'"
            await self._client.put(f"/api/v1/meetings/{eid}", json_body={"title": new_name}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"title": new_name})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, new_name=new_name, endpoint=f"PUT /api/v1/meetings/{eid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.ADD_PARTICIPANT:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to add a participant to. Please specify the meeting name."
            participant_name = extract_participant_name(context.message)
            if not participant_name:
                return "Please specify who to add. For example: 'Add Aryan to Demo'"
            user_id = await self._resolve_user_id(participant_name, token)
            if user_id is None:
                return f"I couldn't find a user named '{participant_name}'. Please check the name."
            await self._client.post(f"/api/v1/meetings/{eid}/participants", params={"user_id": user_id}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"participant": participant_name, "action": "added"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, participant=participant_name, endpoint=f"POST /api/v1/meetings/{eid}/participants", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.REMOVE_PARTICIPANT:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to remove a participant from. Please specify the meeting name."
            participant_name = extract_participant_name(context.message)
            if not participant_name:
                return "Please specify who to remove. For example: 'Remove Aryan from Demo'"
            user_id = await self._resolve_user_id(participant_name, token)
            if user_id is None:
                return f"I couldn't find a user named '{participant_name}'. Please check the name."
            await self._client.post(f"/api/v1/meetings/{eid}/participants/remove", params={"user_id": user_id}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"participant": participant_name, "action": "removed"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, participant=participant_name, endpoint=f"POST /api/v1/meetings/{eid}/participants/remove", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.SHOW_MEETING_DETAIL:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to show. Please specify the meeting name."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"GET /api/v1/meetings/{eid}", elapsed_ms=elapsed)
            return self._formatter.format(intent, data if isinstance(data, dict) else {})

        if intent == IntentType.TODAY_SCHEDULE:
            meetings = await self._client.get("/api/v1/meetings", params={"filter": "today"}, auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /api/v1/meetings?filter=today", event_count=len(meetings), elapsed_ms=elapsed)
            events = [{"title": m.get("title", ""), "time": m.get("start_time") or "TBD", "date": m.get("date") or ""} for m in (meetings or [])]
            return self._formatter.format(intent, {"events": events})

        if intent == IntentType.WEEK_SCHEDULE:
            meetings = await self._client.get("/api/v1/meetings", params={"filter": "weekly"}, auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /api/v1/meetings?filter=weekly", event_count=len(meetings), elapsed_ms=elapsed)
            events = [{"title": m.get("title", ""), "time": m.get("start_time") or "TBD", "date": m.get("date") or ""} for m in (meetings or [])]
            return self._formatter.format(intent, {"events": events})

        if intent == IntentType.UPLOAD_MOM:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to upload MOM for. Please specify the meeting."
            mom_text = extract_mom_text(context.message)
            if not mom_text or mom_text == context.message.strip():
                return "Please provide the meeting minutes text. For example: 'Upload MOM for meeting <name> - <minutes text>'"
            data = await self._client.post(f"/api/v1/meetings/{eid}/mom", json_body={"summary": mom_text}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"meeting_id": eid})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"POST /api/v1/meetings/{eid}/mom", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.EXTRACT_TASKS_FROM_MOM:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to extract tasks from. Please specify the meeting."
            meeting_data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            mom_summary = meeting_data.get("mom_summary") if isinstance(meeting_data, dict) else None
            if not mom_summary:
                return "This meeting doesn't have Minutes of Meeting uploaded yet. Please upload MOM first."
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"meeting_id": eid, "tasks": [], "mom_summary": mom_summary[:200]})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"GET /api/v1/meetings/{eid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.ACCEPT_MEETING:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to accept. Please specify the meeting."
            await self._client.post(f"/api/v1/meetings/{eid}/accept", auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"action": "accepted"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"POST /api/v1/meetings/{eid}/accept", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.DECLINE_MEETING:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to decline. Please specify the meeting."
            await self._client.post(f"/api/v1/meetings/{eid}/decline", auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"action": "declined"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"POST /api/v1/meetings/{eid}/decline", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.SHOW_MEETINGS:
            meetings = await self._client.get("/api/v1/meetings", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /api/v1/meetings", event_count=len(meetings), elapsed_ms=elapsed)
            events = [{"title": m.get("title", ""), "time": m.get("start_time") or "Not scheduled", "date": m.get("date") or "Not scheduled"} for m in (meetings or [])]
            return self._formatter.format(intent, {"events": events})

        if intent == IntentType.TODAY_MEETINGS:
            meetings = await self._client.get("/api/v1/meetings", params={"filter": "today"}, auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /api/v1/meetings?filter=today", event_count=len(meetings), elapsed_ms=elapsed)
            events = [{"title": m.get("title", ""), "time": m.get("start_time") or "Not scheduled", "date": m.get("date") or "Not scheduled"} for m in (meetings or [])]
            return self._formatter.format(intent, {"events": events})

        if intent == IntentType.UPCOMING_MEETINGS:
            meetings = await self._client.get("/api/v1/meetings", params={"filter": "weekly"}, auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /api/v1/meetings?filter=weekly", event_count=len(meetings), elapsed_ms=elapsed)
            events = [{"title": m.get("title", ""), "time": m.get("start_time") or "Not scheduled", "date": m.get("date") or "Not scheduled"} for m in (meetings or [])]
            return self._formatter.format(intent, {"events": events})

        if intent == IntentType.SHOW_MEETING_TIMELINE:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting's timeline to show. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}/timeline", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"GET /api/v1/meetings/{eid}/timeline", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "timeline": data if isinstance(data, list) else []})

        if intent == IntentType.ANALYZE_MOM:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to analyze. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            mom_summary = data.get("mom_summary") if isinstance(data, dict) else None
            if not mom_summary:
                return "This meeting doesn't have Minutes of Meeting uploaded yet. Please upload MOM first."
            analyze_result = await self._client.post(f"/api/v1/meetings/{eid}/mom/analyze", auth_token=token)
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"POST /api/v1/meetings/{eid}/mom/analyze", elapsed_ms=elapsed)
            return self._formatter.format(intent, {
                "meeting_id": eid,
                "mom_summary": mom_summary,
                "executive_summary": data.get("mom_executive_summary", ""),
                "decisions": data.get("mom_decisions", []),
                "risks": data.get("mom_risks", []),
                "followups": data.get("mom_followups", []),
                "blockers": data.get("mom_blockers", []),
            })

        if intent == IntentType.SHOW_EXTRACTED_TASKS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to show extracted tasks for. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}/extracted-tasks", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"GET /api/v1/meetings/{eid}/extracted-tasks", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "tasks": data if isinstance(data, list) else []})

        if intent == IntentType.APPROVE_EXTRACTED_TASKS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to approve tasks for. Please specify the meeting."
            import re as _re
            task_ids = [int(x) for x in _re.findall(r'\b(\d+)\b', context.message) if x.isdigit()]
            if not task_ids:
                tasks_data = await self._client.get(f"/api/v1/meetings/{eid}/extracted-tasks", auth_token=token)
                pending = [t.get("id") for t in (tasks_data if isinstance(tasks_data, list) else []) if t.get("status") == "pending"]
                if pending:
                    task_ids = pending
                else:
                    return "No pending extracted tasks found to approve."
            await self._client.post(f"/api/v1/meetings/{eid}/extracted-tasks/bulk-approve", json_body={"task_ids": task_ids}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"meeting_id": eid, "approved_count": len(task_ids)})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, task_ids=task_ids, elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.REJECT_EXTRACTED_TASKS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to reject tasks for. Please specify the meeting."
            import re as _re
            task_ids = [int(x) for x in _re.findall(r'\b(\d+)\b', context.message) if x.isdigit()]
            if not task_ids:
                return "Please specify which extracted task IDs to reject. For example: 'reject task 1 task 2 from meeting X'"
            await self._client.post(f"/api/v1/meetings/{eid}/extracted-tasks/bulk-reject", json_body={"task_ids": task_ids}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"meeting_id": eid, "rejected_count": len(task_ids)})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, task_ids=task_ids, elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}" if suggestion else result

        if intent == IntentType.WHO_ACCEPTED:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to check. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            participants = data.get("participants", []) if isinstance(data, dict) else []
            accepted = [p.get("user_name", p.get("username", "Unknown")) for p in participants if p.get("status") == "accepted"]
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, accepted_count=len(accepted), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "accepted": accepted})

        if intent == IntentType.WHO_DECLINED:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to check. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            participants = data.get("participants", []) if isinstance(data, dict) else []
            declined = [p.get("user_name", p.get("username", "Unknown")) for p in participants if p.get("status") == "declined"]
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, declined_count=len(declined), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "declined": declined})

        if intent == IntentType.SHOW_MEETING_DECISIONS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to check. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            decisions = data.get("mom_decisions", []) if isinstance(data, dict) else []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "decisions": decisions})

        if intent == IntentType.SHOW_MEETING_RISKS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to check. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            risks = data.get("mom_risks", []) if isinstance(data, dict) else []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "risks": risks})

        if intent == IntentType.SHOW_MEETING_FOLLOWUPS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to check. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            followups = data.get("mom_followups", []) if isinstance(data, dict) else []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "followups": followups})

        if intent == IntentType.SHOW_MEETING_BLOCKERS:
            eid = await self._resolve_meeting_id(context.message, token)
            if eid is None:
                return "I couldn't find which meeting to check. Please specify the meeting."
            data = await self._client.get(f"/api/v1/meetings/{eid}", auth_token=token)
            blockers = data.get("mom_blockers", []) if isinstance(data, dict) else []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, elapsed_ms=elapsed)
            return self._formatter.format(intent, {"meeting_id": eid, "blockers": blockers})

        return "I'm not sure how to handle that request."

    async def _resolve_meeting_id(self, message: str, token: str) -> int | None:
        eid = extract_event_id(message)
        if eid and eid != "default":
            if eid.isdigit():
                return int(eid)
            meetings = await self._client.get("/api/v1/meetings", auth_token=token)
            lower_name = eid.lower()
            exact = None
            contains_eid = None
            contains_title = None
            for m in (meetings or []):
                title = m.get("title", "").lower()
                if title == lower_name:
                    return m.get("id")
                if lower_name in title and contains_eid is None:
                    contains_eid = m.get("id")
                if title in lower_name and contains_title is None:
                    contains_title = m.get("id")
            if contains_eid is not None:
                return contains_eid
            if contains_title is not None:
                return contains_title
        meetings = await self._client.get("/api/v1/meetings", params={"filter": "today"}, auth_token=token)
        if meetings and len(meetings) == 1:
            return meetings[0].get("id")
        return None

    async def _resolve_user_id(self, name: str, token: str) -> int | None:
        users = await self._client.get("/api/v1/users", auth_token=token)
        lower_name = name.lower()
        for u in (users if isinstance(users, list) else []):
            full_name = (u.get("full_name") or "").lower()
            email = (u.get("email") or "").lower()
            if lower_name in full_name or full_name in lower_name or lower_name in email:
                return u.get("id")
        return None

    def name(self) -> str:
        return "PlannerTool"

    def description(self) -> str:
        return "Manage schedule — meetings, reminders, daily and weekly views."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "add_meeting",
            "cancel_meeting",
            "reschedule_meeting",
            "rename_meeting",
            "add_participant",
            "remove_participant",
            "show_meeting_detail",
            "today_schedule",
            "week_schedule",
            "add_reminder",
            "show_meetings",
            "today_meetings",
            "upcoming_meetings",
            "show_meeting_timeline",
            "upload_mom",
            "analyze_mom",
            "extract_tasks_from_mom",
            "show_extracted_tasks",
            "approve_extracted_tasks",
            "reject_extracted_tasks",
            "who_accepted",
            "who_declined",
            "accept_meeting",
            "decline_meeting",
            "show_meeting_decisions",
            "show_meeting_risks",
            "show_meeting_followups",
            "show_meeting_blockers",
        ]
