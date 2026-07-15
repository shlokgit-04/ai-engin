import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import NotificationListResponse, APIResponse
from app.integrations.backend.exceptions import (
    BackendNotFoundError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.executive.params import extract_notification_id
from app.executive.suggestions import get_suggestion
from app.core.logging import logger


_FALLBACK: dict[str, str] = {}

_ERROR_MAP: dict[type, str] = {
    BackendNotFoundError: "I couldn't find that notification.",
    BackendConnectionError: "I couldn't reach the backend service.",
    BackendTimeoutError: "The backend took too long to respond.",
    BackendServerError: "The backend is currently unavailable.",
}


class NotificationTool(BaseTool):
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
            logger.warning("NotificationTool error", intent=intent.value, error=str(exc))
            return msg
        except Exception:
            logger.exception("NotificationTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()

        if intent == IntentType.SHOW_NOTIFICATIONS:
            data = await self._client.get("/notifications")
            resp = NotificationListResponse(**data)
            notifications = resp.data or []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("NotificationTool executed", intent=intent.value, endpoint="GET /notifications", count=len(notifications), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"notifications": [n.model_dump() for n in notifications]})

        if intent == IntentType.CREATE_NOTIFICATION:
            data = await self._client.post("/notifications", json_body={"text": context.message})
            resp = APIResponse(**data)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, resp.model_dump())
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("NotificationTool executed", intent=intent.value, endpoint="POST /notifications", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.MARK_AS_READ:
            nid = extract_notification_id(context.message)
            if not nid:
                return "I couldn't determine which notification you want to mark as read."
            data = await self._client.put(f"/notifications/{nid}/read")
            resp = APIResponse(**data)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, resp.model_dump())
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("NotificationTool executed", intent=intent.value, notification_id=nid, endpoint=f"PUT /notifications/{nid}/read", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        return "I'm not sure how to handle that request."

    def name(self) -> str:
        return "NotificationTool"

    def description(self) -> str:
        return "Manage notifications — create, list, and mark as read."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "create_notification",
            "show_notifications",
            "mark_as_read",
        ]
