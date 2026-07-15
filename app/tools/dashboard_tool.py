import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import DashboardResponse
from app.integrations.backend.exceptions import (
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.core.logging import logger


_ERROR_MAP: dict[type, str] = {
    BackendConnectionError: "I couldn't reach the backend service.",
    BackendTimeoutError: "The backend took too long to respond.",
    BackendServerError: "The backend is currently unavailable.",
}


class DashboardTool(BaseTool):
    def __init__(
        self,
        client: BackendClient | None = None,
        formatter: ResponseFormatter | None = None,
    ) -> None:
        self._client = client or BackendClient()
        self._formatter = formatter or ResponseFormatter()

    async def execute(self, context: ExecutionContext, intent: IntentType) -> str:
        try:
            return await self._route(context, intent)
        except tuple(_ERROR_MAP) as exc:
            msg = _ERROR_MAP.get(type(exc), "An unexpected error occurred.")
            logger.warning("DashboardTool error", intent=intent.value, error=str(exc))
            return msg
        except Exception:
            logger.exception("DashboardTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()
        data = await self._client.get("/dashboard/summary")
        resp = DashboardResponse(**data)
        dump = resp.model_dump()

        if intent == IntentType.FOCUS_TODAY:
            focus = resp.data.focus if resp.data else "No focus available"
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"focus": focus})

        if intent == IntentType.EXECUTIVE_SUMMARY:
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, dump.get("data", {}) | {"focus": resp.data.focus if resp.data else ""})

        if intent == IntentType.TODAY_PRIORITIES:
            priorities = resp.data.priorities if resp.data else []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"priorities": priorities})

        if intent == IntentType.BUSINESS_RISK:
            risks = resp.data.risks if resp.data else []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("DashboardTool executed", intent=intent.value, endpoint="GET /dashboard/summary", elapsed_ms=elapsed)
            return self._formatter.format(intent, {"risks": risks})

        return "I'm not sure how to handle that request."

    def name(self) -> str:
        return "DashboardTool"

    def description(self) -> str:
        return "Executive dashboard — daily focus, summary, priorities, risk assessment."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "focus_today",
            "executive_summary",
            "today_priorities",
            "business_risk",
        ]
