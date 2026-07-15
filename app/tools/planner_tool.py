import time
import re

import httpx

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.response.formatter import ResponseFormatter
from app.executive.params import extract_event_title, extract_date, extract_time
from app.executive.validation import validate_not_empty
from app.executive.suggestions import get_suggestion
from app.core.logging import logger


_MEETING_BASE = "http://localhost:8000"
_AUTH_EMAIL = "vincent@nurofin.com"
_AUTH_PASSWORD = "qwerty"


class _MeetingClient:
    """Lightweight async HTTP client for the backend meeting API with auth."""

    def __init__(self, base_url: str = _MEETING_BASE) -> None:
        self._base = base_url.rstrip("/")
        self._token: str | None = None
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _ensure_auth(self) -> str:
        if self._token:
            return self._token
        resp = await self._client.post(
            f"{self._base}/api/v1/auth/login",
            data={"username": _AUTH_EMAIL, "password": _AUTH_PASSWORD},
        )
        resp.raise_for_status()
        payload = resp.json()
        self._token = payload["data"]["access_token"]
        return self._token

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    async def get(self, path: str, params: dict | None = None) -> dict:
        token = await self._ensure_auth()
        resp = await self._client.get(
            f"{self._base}{path}", headers=self._headers(token), params=params,
        )
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json_body: dict | None = None, params: dict | None = None) -> dict:
        token = await self._ensure_auth()
        resp = await self._client.post(
            f"{self._base}{path}", headers=self._headers(token),
            json=json_body, params=params,
        )
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, json_body: dict | None = None) -> dict:
        token = await self._ensure_auth()
        resp = await self._client.put(
            f"{self._base}{path}", headers=self._headers(token), json=json_body,
        )
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str) -> dict:
        token = await self._ensure_auth()
        resp = await self._client.delete(
            f"{self._base}{path}", headers=self._headers(token),
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()


class PlannerTool(BaseTool):
    def __init__(
        self,
        client: _MeetingClient | None = None,
        formatter: ResponseFormatter | None = None,
    ) -> None:
        self._client = client or _MeetingClient()
        self._formatter = formatter or ResponseFormatter()

    async def execute(self, context: ExecutionContext, intent: IntentType) -> str:
        try:
            return await self._route(context, intent)
        except httpx.HTTPStatusError as exc:
            logger.warning("PlannerTool HTTP error", intent=intent.value, status=exc.response.status_code)
            return f"Backend error: {exc.response.status_code}"
        except Exception:
            logger.exception("PlannerTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()
        result: str | None = None

        if intent == IntentType.SHOW_MEETINGS:
            result = await self._show_meetings(context)
        elif intent == IntentType.TODAY_MEETINGS:
            result = await self._show_meetings(context, filter_="today")
        elif intent == IntentType.UPCOMING_MEETINGS:
            result = await self._show_meetings(context, filter_="weekly")
        elif intent == IntentType.ADD_MEETING:
            result = await self._add_meeting(context)
        elif intent == IntentType.CANCEL_MEETING:
            result = await self._cancel_meeting(context)
        elif intent == IntentType.RESCHEDULE_MEETING:
            result = await self._reschedule_meeting(context)
        elif intent == IntentType.RENAME_MEETING:
            result = await self._rename_meeting(context)
        elif intent == IntentType.SHOW_MEETING_DETAIL:
            result = await self._show_meeting_detail(context)
        elif intent == IntentType.ADD_PARTICIPANT:
            result = await self._add_participant(context)
        elif intent == IntentType.REMOVE_PARTICIPANT:
            result = await self._remove_participant(context)
        elif intent == IntentType.UPLOAD_MOM:
            result = await self._upload_mom(context)
        elif intent == IntentType.ANALYZE_MOM:
            result = await self._analyze_mom(context)
        elif intent == IntentType.EXTRACT_TASKS_FROM_MOM:
            result = await self._extract_tasks(context)
        elif intent == IntentType.SHOW_EXTRACTED_TASKS:
            result = await self._show_extracted_tasks(context)
        elif intent == IntentType.APPROVE_EXTRACTED_TASKS:
            result = await self._approve_extracted_tasks(context)
        elif intent == IntentType.REJECT_EXTRACTED_TASKS:
            result = await self._reject_extracted_tasks(context)
        elif intent == IntentType.ACCEPT_MEETING:
            result = await self._accept_meeting(context)
        elif intent == IntentType.DECLINE_MEETING:
            result = await self._decline_meeting(context)
        elif intent == IntentType.WHO_ACCEPTED:
            result = await self._who_accepted_declined(context, status_filter="accepted")
        elif intent == IntentType.WHO_DECLINED:
            result = await self._who_accepted_declined(context, status_filter="declined")
        elif intent == IntentType.SHOW_MEETING_TIMELINE:
            result = await self._show_timeline(context)
        elif intent == IntentType.SHOW_MEETING_DECISIONS:
            result = await self._show_mom_field(context, "decisions")
        elif intent == IntentType.SHOW_MEETING_RISKS:
            result = await self._show_mom_field(context, "risks")
        elif intent == IntentType.SHOW_MEETING_FOLLOWUPS:
            result = await self._show_mom_field(context, "followups")
        elif intent == IntentType.SHOW_MEETING_BLOCKERS:
            result = await self._show_mom_field(context, "blockers")
        elif intent == IntentType.TODAY_SCHEDULE:
            result = await self._show_meetings(context, filter_="today")
        elif intent == IntentType.WEEK_SCHEDULE:
            result = await self._show_meetings(context, filter_="weekly")

        if result is None:
            result = "I'm not sure how to handle that request."

        elapsed = round((time.monotonic() - start) * 1000, 2)
        logger.info("PlannerTool executed", intent=intent.value, elapsed_ms=elapsed)
        return result

    # ── Helpers ─────────────────────────────────────────────────────────

    async def _resolve_meeting_id(self, message: str) -> int | None:
        """Find a meeting by ID or title fuzzy-match."""
        lower = message.lower()
        words = lower.split()

        # 1. Try numeric ID after meeting/event keyword
        for i, w in enumerate(words):
            if w in ("meeting", "event", "#") and i + 1 < len(words):
                candidate = words[i + 1].strip(".,!?")
                if candidate.isdigit():
                    return int(candidate)

        # 2. Extract a clean title and search
        title = self._extract_meeting_title_from_text(lower)
        if title:
            data = await self._client.get("/api/v1/meetings", params={"search": title})
            meetings = data.get("data", [])
            if not meetings:
                # try each word
                for word in title.split():
                    if len(word) > 2:
                        data = await self._client.get("/api/v1/meetings", params={"search": word})
                        meetings = data.get("data", [])
                        if meetings:
                            break
            for m in meetings:
                if title in m.get("title", "").lower():
                    return m["id"]
            if meetings:
                return meetings[0]["id"]

        return None

    def _extract_meeting_title_from_text(self, lower: str) -> str | None:
        """Pull a meeting title from freeform text."""
        stop_words = {
            "show", "list", "all", "my", "the", "a", "an", "and", "or",
            "to", "from", "for", "in", "on", "at", "with", "by",
            "details", "detail", "info", "information",
            "timeline", "history", "activity",
            "decisions", "risks", "follow-ups", "followups", "blockers",
            "tasks", "participants", "accepted", "declined",
            "upload", "analyze", "extract", "approve", "reject",
            "accept", "decline", "add", "remove", "rename",
            "create", "schedule", "book", "cancel", "delete",
            "today", "tomorrow", "upcoming", "weekly", "this",
            "meeting", "meetings", "event", "events",
            "mom", "minutes", "notes",
            "called", "named", "titled",
            "who", "what", "when", "where",
            "is", "are", "was", "were", "has", "have",
        }

        # Pattern: "show meeting <title>" / "show meeting details for <title>"
        # Pattern: "<verb> meeting <title> [to <new_name>]"
        # Pattern: "<verb> mom for meeting <title>"
        patterns = [
            # "show meeting <title>"
            r"(?:show|list|view|get)\s+(?:the\s+)?(?:meeting|event)\s+(?:details?\s*(?:of|for|about)?\s*)?(?:called\s+|named\s+|titled\s+)?(.+?)(?:\s*$)",
            # "meeting details for <title>"
            r"(?:meeting|event)\s+(?:details?\s*(?:of|for|about)?)\s+(?:the\s+)?(?:called\s+|named\s+|titled\s+)?(.+?)(?:\s*$)",
            # "add Aryan to meeting <title>" or "remove Aryan from meeting <title>"
            r"(?:add|remove|invite)\s+\S+\s+(?:to|from)\s+(?:the\s+)?(?:meeting|event)\s+(.+?)(?:\s*$)",
            # "rename meeting <old> to <new>"
            r"(?:rename|cancel|delete|reschedule|accept|decline)\s+(?:the\s+)?(?:meeting|event)\s+(.+?)(?:\s+to\s+|$)",
            # "upload mom for meeting <title>: content" or "upload mom <title>"
            r"(?:upload|analyze|extract)\s+(?:mom|minutes|meeting\s+notes?)\s+(?:for|of|from|in)?\s*(?:the\s+)?(?:meeting\s+)?(.+?)(?:\s*:\s*|$)",
            # "extract tasks from meeting <title>" or "approve extracted tasks for meeting <title>"
            r"(?:extract|show|get|pull|approve|reject)\s+(?:extracted\s+)?tasks?\s+(?:from|for|of)\s+(?:the\s+)?(?:meeting|event)\s+(.+?)(?:\s*$)",
            # "show decisions for meeting <title>"
            r"(?:show|what|list|show)\s+(?:decisions|risks|follow.?ups?|blockers?)\s+(?:for|of|from|in)?\s*(?:the\s+)?(?:meeting\s+)?(.+?)(?:\s*$)",
            # "who accepted meeting <title>"
            r"(?:who|which)\s+(?:accepted|declined|confirmed)\s+(?:the\s+)?(?:meeting|event)\s+(.+?)(?:\s*$)",
        ]
        for pat in patterns:
            m = re.search(pat, lower)
            if m:
                candidate = m.group(1).strip()
                words = candidate.split()
                filtered = [w for w in words if w not in stop_words and not w.startswith("@")]
                if filtered:
                    return " ".join(filtered).strip(".,!? ")

        # Generic: try to find quoted title
        m = re.search(r'"([^"]+)"', lower)
        if m:
            return m.group(1).strip()

        return None

    async def _resolve_user_id(self, message: str) -> int | None:
        """Find a user ID by name from the message."""
        lower = message.lower()
        words = lower.split()

        # 1. Try after "add X to" / "remove X from" / "invite X to"
        for pattern in [
            r"(?:add|remove|invite)\s+(\S+)\s+(?:to|from|into)",
            r"(?:add|remove|invite)\s+(\S+)\s+(?:meeting|event)",
        ]:
            m = re.search(pattern, lower)
            if m:
                name = m.group(1).strip(".,!?@")
                if name and name not in ("a", "an", "the", "to", "from", "meeting", "event", "participant", "member"):
                    uid = await self._find_user_by_name(name)
                    if uid:
                        return uid

        # 2. Fallback: look for capitalized words that might be names
        for i, w in enumerate(words):
            if w in ("add", "remove", "invite") and i + 1 < len(words):
                next_w = words[i + 1].strip(".,!?@")
                if next_w and next_w not in ("a", "an", "the", "to", "from", "meeting", "event", "participant", "member", "user"):
                    uid = await self._find_user_by_name(next_w)
                    if uid:
                        return uid

        return None

    async def _find_user_by_name(self, name: str) -> int | None:
        """Search users by name and return matching user ID."""
        data = await self._client.get("/api/v1/users")
        users = data.get("data", [])
        lower_name = name.lower()
        for u in users:
            if (lower_name in u.get("full_name", "").lower()
                    or lower_name in u.get("email", "").lower()
                    or lower_name in u.get("username", "").lower()):
                return u["id"]
        return None

    def _extract_mom_text(self, message: str) -> str:
        """Extract MOM content from the user message."""
        lower = message.lower()
        # "upload mom for meeting <title>: <content>"
        m = re.search(r"(?:upload|save)\s+(?:mom|minutes)\s+(?:for|of|from|in)?\s*(?:the\s+)?(?:meeting\s+)?[^:]*:\s*(.+)", lower)
        if m:
            return m.group(1).strip()
        # "upload mom for meeting <title>" — content after the meeting reference
        for marker in ["for meeting", "for the meeting", "of meeting", "of the meeting"]:
            if marker in lower:
                idx = lower.index(marker) + len(marker)
                rest = message[idx:].strip()
                if rest:
                    return rest
        return message

    def _extract_task_ids_from_text(self, message: str) -> list[int]:
        """Extract task IDs from a message like 'approve task 1 and 3'."""
        ids = []
        for m in re.finditer(r"\b(\d+)\b", message):
            val = int(m.group(1))
            if val > 0 and val < 10000:
                ids.append(val)
        return ids

    # ── Intent handlers ─────────────────────────────────────────────────

    async def _show_meetings(self, ctx: ExecutionContext, filter_: str | None = None) -> str:
        params: dict = {}
        if filter_:
            params["filter"] = filter_
        data = await self._client.get("/api/v1/meetings", params=params)
        meetings = data.get("data", [])
        if not meetings:
            return "You have no meetings at the moment."
        lines = []
        for m in meetings:
            date_str = m.get("date") or "No date"
            time_str = m.get("start_time") or ""
            lines.append(f"- **{m['title']}** (ID: {m['id']}) — {date_str} {time_str}")
        header = "Today's meetings:" if filter_ == "today" else "This week's meetings:" if filter_ == "weekly" else "Your meetings:"
        return header + "\n" + "\n".join(lines)

    async def _add_meeting(self, ctx: ExecutionContext) -> str:
        title = extract_event_title(ctx.message, "Meeting")
        # Clean up title: remove date/time/noise words
        title = self._clean_title(title)
        valid, err = validate_not_empty(title, "Meeting title")
        if not valid:
            return err
        event_date = extract_date(ctx.message)
        event_time = extract_time(ctx.message)
        body: dict = {"title": title}
        if event_date:
            body["date"] = event_date
        if event_time:
            body["start_time"] = event_time
        data = await self._client.post("/api/v1/meetings", json_body=body)
        meeting = data.get("data", {})
        suggestion = get_suggestion("add_meeting")
        result = self._formatter.format(IntentType.ADD_MEETING, {
            "date": event_date or "Not set",
            "time": event_time or "TBD",
            "title": title,
        })
        return f"{result}\n\n{suggestion}" if suggestion else result

    def _clean_title(self, raw: str) -> str:
        """Remove noise words from a meeting title."""
        noise = {
            "called", "named", "titled", "tomorrow", "today", "at",
            "am", "pm", "noon", "morning", "afternoon", "evening",
            "next", "week", "monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday",
        }
        words = raw.split()
        cleaned = []
        skip_next = False
        for w in words:
            wl = w.lower().strip(".,!?")
            if wl in noise:
                continue
            # skip time-like patterns "3pm", "10:00", etc.
            if re.match(r"^\d{1,2}(:\d{2})?\s*(am|pm)?$", wl):
                skip_next = True
                continue
            if skip_next and wl in ("am", "pm"):
                skip_next = False
                continue
            skip_next = False
            cleaned.append(w)
        return " ".join(cleaned).strip() or "Meeting"

    async def _cancel_meeting(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting would you like to cancel? Please specify the meeting name or ID."
        await self._client.delete(f"/api/v1/meetings/{mid}")
        suggestion = get_suggestion("cancel_meeting")
        result = f"Meeting (ID: {mid}) has been cancelled."
        return f"{result}\n\n{suggestion}" if suggestion else result

    async def _reschedule_meeting(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting would you like to reschedule? Please specify the meeting name or ID."
        new_date = extract_date(ctx.message)
        new_time = extract_time(ctx.message)
        body: dict = {}
        if new_date:
            body["date"] = new_date
        if new_time:
            body["start_time"] = new_time
        if not body:
            return "Please specify a new date or time for the meeting."
        await self._client.put(f"/api/v1/meetings/{mid}", json_body=body)
        return f"Meeting (ID: {mid}) has been rescheduled."

    async def _rename_meeting(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting would you like to rename? Please specify the meeting name or ID."
        new_name = self._extract_rename_target(ctx.message)
        if not new_name:
            return "What should the new name be? Use 'rename meeting X to Y'."
        await self._client.put(f"/api/v1/meetings/{mid}", json_body={"title": new_name})
        return f"Meeting (ID: {mid}) renamed to '{new_name}'."

    def _extract_rename_target(self, message: str) -> str:
        lower = message.lower()
        for prefix in ("rename meeting to", "rename event to", "rename to"):
            if prefix in lower:
                idx = lower.index(prefix) + len(prefix)
                return message[idx:].strip(".,!? ") or ""
        # try "rename meeting X to Y" pattern
        m = re.search(r"rename\s+(?:meeting|event)\s+.+?\s+to\s+(.+)", lower)
        if m:
            return m.group(1).strip(".,!? ") or ""
        return ""

    async def _show_meeting_detail(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        data = await self._client.get(f"/api/v1/meetings/{mid}")
        m = data.get("data", {})
        lines = [f"**{m.get('title', 'Meeting')}** (ID: {m['id']})"]
        if m.get("date"):
            lines.append(f"Date: {m['date']}")
        if m.get("start_time"):
            lines.append(f"Time: {m['start_time']}")
        if m.get("location"):
            lines.append(f"Location: {m['location']}")
        if m.get("agenda"):
            lines.append(f"Agenda: {m['agenda']}")
        participants = m.get("participants", [])
        if participants:
            p_strs = [f"{p.get('user_name', 'Unknown')} ({p.get('status', 'unknown')})" for p in participants]
            lines.append(f"Participants: {', '.join(p_strs)}")
        if m.get("mom_summary"):
            lines.append(f"MOM: {m['mom_summary']}")
        return "\n".join(lines)

    async def _add_participant(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        uid = await self._resolve_user_id(ctx.message)
        if uid is None:
            return "Who would you like to add? Please specify a participant name."
        await self._client.post(f"/api/v1/meetings/{mid}/participants", params={"user_id": uid})
        return f"Participant (user ID: {uid}) added to meeting (ID: {mid})."

    async def _remove_participant(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        uid = await self._resolve_user_id(ctx.message)
        if uid is None:
            return "Who would you like to remove? Please specify a participant name."
        await self._client.post(f"/api/v1/meetings/{mid}/participants/remove", params={"user_id": uid})
        return f"Participant (user ID: {uid}) removed from meeting (ID: {mid})."

    async def _upload_mom(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        mom_text = self._extract_mom_text(ctx.message)
        valid, err = validate_not_empty(mom_text, "MOM content")
        if not valid:
            return "Please provide the minutes of meeting content."
        await self._client.post(f"/api/v1/meetings/{mid}/mom", json_body={"summary": mom_text})
        return f"MOM uploaded for meeting (ID: {mid})."

    async def _analyze_mom(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        data = await self._client.post(f"/api/v1/meetings/{mid}/mom/analyze")
        if not data.get("success"):
            return f"Analysis failed: {data.get('message', 'Unknown error')}"
        analysis = data.get("data", {})
        tasks = analysis.get("extracted_tasks", [])
        meeting_data = analysis.get("meeting", analysis)
        lines = ["MOM Analysis complete for meeting (ID: {})".format(mid)]
        if meeting_data.get("mom_executive_summary"):
            lines.append(f"\n**Executive Summary:** {meeting_data['mom_executive_summary']}")
        if meeting_data.get("mom_decisions"):
            lines.append(f"\n**Decisions:** {meeting_data['mom_decisions']}")
        if meeting_data.get("mom_risks"):
            lines.append(f"\n**Risks:** {meeting_data['mom_risks']}")
        if meeting_data.get("mom_followups"):
            lines.append(f"\n**Follow-ups:** {meeting_data['mom_followups']}")
        if meeting_data.get("mom_blockers"):
            lines.append(f"\n**Blockers:** {meeting_data['mom_blockers']}")
        if tasks:
            lines.append(f"\n**{len(tasks)} task(s) extracted.**")
        return "\n".join(lines)

    async def _extract_tasks(self, ctx: ExecutionContext) -> str:
        """Alias: same as analyze_mom for extracting tasks from MOM."""
        return await self._analyze_mom(ctx)

    async def _show_extracted_tasks(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        data = await self._client.get(f"/api/v1/meetings/{mid}/extracted-tasks")
        tasks = data.get("data", [])
        if not tasks:
            return f"No extracted tasks for meeting (ID: {mid})."
        lines = [f"**Extracted Tasks for Meeting {mid}:**"]
        for t in tasks:
            status = t.get("status", "pending")
            lines.append(f"- [{status.upper()}] {t.get('title', 'Untitled')} (ID: {t['id']}, confidence: {t.get('confidence', 'N/A')}%)")
        return "\n".join(lines)

    async def _approve_extracted_tasks(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        task_ids = self._extract_task_ids_from_text(ctx.message)
        if not task_ids:
            # approve all pending
            data = await self._client.get(f"/api/v1/meetings/{mid}/extracted-tasks")
            tasks = data.get("data", [])
            task_ids = [t["id"] for t in tasks if t.get("status") == "pending"]
        if not task_ids:
            return "No pending tasks to approve."
        results = []
        for tid in task_ids:
            try:
                resp = await self._client.post(f"/api/v1/meetings/{mid}/extracted-tasks/{tid}/approve")
                results.append(f"Task {tid}: approved")
            except Exception as exc:
                results.append(f"Task {tid}: failed ({exc})")
        return "\n".join(results)

    async def _reject_extracted_tasks(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        task_ids = self._extract_task_ids_from_text(ctx.message)
        if not task_ids:
            data = await self._client.get(f"/api/v1/meetings/{mid}/extracted-tasks")
            tasks = data.get("data", [])
            task_ids = [t["id"] for t in tasks if t.get("status") == "pending"]
        if not task_ids:
            return "No pending tasks to reject."
        results = []
        for tid in task_ids:
            try:
                resp = await self._client.post(f"/api/v1/meetings/{mid}/extracted-tasks/{tid}/reject")
                results.append(f"Task {tid}: rejected")
            except Exception as exc:
                results.append(f"Task {tid}: failed ({exc})")
        return "\n".join(results)

    async def _accept_meeting(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting would you like to accept?"
        data = await self._client.post(f"/api/v1/meetings/{mid}/accept")
        return data.get("message", "Meeting accepted.")

    async def _decline_meeting(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting would you like to decline?"
        data = await self._client.post(f"/api/v1/meetings/{mid}/decline")
        return data.get("message", "Meeting declined.")

    async def _who_accepted_declined(self, ctx: ExecutionContext, status_filter: str) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        data = await self._client.get(f"/api/v1/meetings/{mid}")
        meeting = data.get("data", {})
        participants = meeting.get("participants", [])
        matched = [p for p in participants if p.get("status") == status_filter]
        if not matched:
            return f"Nobody has {status_filter} meeting (ID: {mid}) yet."
        names = [p.get("user_name", f"User {p.get('user_id', '?')}") for p in matched]
        return f"**{status_filter.title()} meeting {mid}:** {', '.join(names)}"

    async def _show_timeline(self, ctx: ExecutionContext) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        data = await self._client.get(f"/api/v1/meetings/{mid}/timeline")
        events = data.get("data", [])
        if not events:
            return f"No timeline events for meeting (ID: {mid})."
        lines = [f"**Timeline for Meeting {mid}:**"]
        for e in events:
            ts = e.get("created_at", "")[:19]
            lines.append(f"- [{ts}] {e.get('action', '')}: {e.get('description', '')}")
        return "\n".join(lines)

    async def _show_mom_field(self, ctx: ExecutionContext, field: str) -> str:
        mid = await self._resolve_meeting_id(ctx.message)
        if mid is None:
            return "Which meeting? Please specify the meeting name or ID."
        data = await self._client.get(f"/api/v1/meetings/{mid}")
        meeting = data.get("data", {})
        field_map = {
            "decisions": "mom_decisions",
            "risks": "mom_risks",
            "followups": "mom_followups",
            "blockers": "mom_blockers",
        }
        value = meeting.get(field_map.get(field, field))
        if not value:
            return f"No {field} recorded for meeting (ID: {mid})."
        return f"**{field.title()} for Meeting {mid}:**\n{value}"

    def name(self) -> str:
        return "PlannerTool"

    def description(self) -> str:
        return "Manage meetings — CRUD, participants, MOM, timeline, extracted tasks."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "add_meeting",
            "cancel_meeting",
            "reschedule_meeting",
            "today_schedule",
            "week_schedule",
            "add_reminder",
            "show_meetings",
            "today_meetings",
            "upcoming_meetings",
            "rename_meeting",
            "show_meeting_detail",
            "add_participant",
            "remove_participant",
            "upload_mom",
            "analyze_mom",
            "extract_tasks_from_mom",
            "show_extracted_tasks",
            "approve_extracted_tasks",
            "reject_extracted_tasks",
            "accept_meeting",
            "decline_meeting",
            "who_accepted",
            "who_declined",
            "show_meeting_timeline",
            "show_meeting_decisions",
            "show_meeting_risks",
            "show_meeting_followups",
            "show_meeting_blockers",
        ]
