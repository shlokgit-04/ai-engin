import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import EventListResponse, StatusResponse
from app.integrations.backend.exceptions import (
    BackendNotFoundError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.executive.params import extract_event_title, extract_event_id, extract_date, extract_time
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

        if intent == IntentType.ADD_MEETING:
            title = extract_event_title(context.message, "Meeting")
            valid, err = validate_not_empty(title, "Meeting title")
            if not valid:
                return err
            event_date = extract_date(context.message) or "Today"
            event_time = extract_time(context.message) or "TBD"
            data = await self._client.post("/planner/events", json_body={"title": title})
            resp = StatusResponse(**data)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"date": event_date, "time": event_time, "title": title})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, title=title, date=event_date, time=event_time, endpoint="POST /planner/events", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.CANCEL_MEETING:
            eid = extract_event_id(context.message)
            await self._client.delete(f"/planner/events/{eid}")
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, endpoint=f"DELETE /planner/events/{eid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.RESCHEDULE_MEETING:
            eid = extract_event_id(context.message)
            new_date = extract_date(context.message) or "today"
            new_time = extract_time(context.message) or "TBD"
            data = await self._client.put(f"/planner/events/{eid}", json_body={"start": f"{new_date} {new_time}"})
            resp = StatusResponse(**data)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, resp.model_dump())
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, event_id=eid, date=new_date, time=new_time, endpoint=f"PUT /planner/events/{eid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.TODAY_SCHEDULE:
            data = await self._client.get("/planner/today")
            resp = EventListResponse(**data)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /planner/today", event_count=len(resp.events), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"events": [e.model_dump() for e in resp.events]})

        if intent == IntentType.WEEK_SCHEDULE:
            data = await self._client.get("/planner/week")
            resp = EventListResponse(**data)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("PlannerTool executed", intent=intent.value, endpoint="GET /planner/week", event_count=len(resp.events), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"events": [e.model_dump() for e in resp.events]})

        return "I'm not sure how to handle that request."

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
            "today_schedule",
            "week_schedule",
            "add_reminder",
        ]
