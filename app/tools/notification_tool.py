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
from app.executive.params import extract_notification_id, extract_notification_title, extract_notification_type
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
        token = context.auth_token

        if intent == IntentType.SHOW_NOTIFICATIONS:
            notifications = await self._client.get("/api/v1/notifications", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("NotificationTool executed", intent=intent.value, endpoint="GET /api/v1/notifications", count=len(notifications), elapsed_ms=elapsed)
            items = [{"text": n.get("message", n.get("title", ""))} for n in (notifications or [])]
            return self._formatter.format(intent, {"notifications": items})

        if intent == IntentType.CREATE_NOTIFICATION:
            title = extract_notification_title(context.message, context.message)
            notif_type = extract_notification_type(context.message)
            await self._client.post("/api/v1/notifications", json_body={
                "title": title,
                "message": context.message,
                "type": notif_type,
                "user_id": 0,
            }, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("NotificationTool executed", intent=intent.value, endpoint="POST /api/v1/notifications", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.MARK_AS_READ:
            nid = extract_notification_id(context.message)
            if nid == "all":
                notifications = await self._client.get("/api/v1/notifications", auth_token=token)
                count = 0
                for n in (notifications or []):
                    if not n.get("is_read"):
                        await self._client.put(f"/api/v1/notifications/{n['id']}/read", auth_token=token)
                        count += 1
                suggestion = get_suggestion(intent.value)
                result = f"Marked {count} notification(s) as read."
                elapsed = round((time.monotonic() - start) * 1000, 2)
                logger.info("NotificationTool executed", intent=intent.value, count=count, elapsed_ms=elapsed)
                return f"{result}\n\n{suggestion}"
            if not nid:
                notifications = await self._client.get("/api/v1/notifications", auth_token=token)
                unread = [n for n in (notifications or []) if not n.get("is_read")]
                if len(unread) == 1:
                    nid = str(unread[0]["id"])
                elif len(unread) > 1:
                    return f"You have {len(unread)} unread notifications. Please specify which one (e.g., 'Mark notification 1 as read') or say 'Mark all as read'."
                else:
                    return "You have no unread notifications."
            if nid and nid != "all":
                await self._client.put(f"/api/v1/notifications/{nid}/read", auth_token=token)
                suggestion = get_suggestion(intent.value)
                result = self._formatter.format(intent, {})
                elapsed = round((time.monotonic() - start) * 1000, 2)
                logger.info("NotificationTool executed", intent=intent.value, notification_id=nid, endpoint=f"PUT /api/v1/notifications/{nid}/read", elapsed_ms=elapsed)
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
