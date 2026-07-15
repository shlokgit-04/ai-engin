import time

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import Task, TaskListResponse, APIResponse
from app.integrations.backend.exceptions import (
    BackendNotFoundError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.executive.params import extract_task_title, extract_task_id, extract_priority, extract_date, extract_task_identifier
from app.executive.validation import validate_not_empty, validate_priority
from app.executive.suggestions import get_suggestion
from app.core.logging import logger


_FALLBACK: dict[str, str] = {}

_ERROR_MAP: dict[type, str] = {
    BackendNotFoundError: "I couldn't find that task.",
    BackendConnectionError: "I couldn't reach the backend service.",
    BackendTimeoutError: "The backend took too long to respond.",
    BackendServerError: "The backend is currently unavailable.",
}


class TaskTool(BaseTool):
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
            logger.warning("TaskTool error", intent=intent.value, error=str(exc))
            return msg
        except Exception:
            logger.exception("TaskTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()

        if intent == IntentType.CREATE_TASK:
            title = extract_task_title(context.message, "New Task")
            valid, err = validate_not_empty(title, "Task title")
            if not valid:
                return err
            priority = extract_priority(context.message)
            due_date = extract_date(context.message) or "Not set"
            data = await self._client.post("/tasks", json_body={"title": title, "status": "pending"})
            resp = APIResponse(**data)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {
                "priority": priority.title(),
                "due_date": due_date,
            })
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, title=title, priority=priority, endpoint="POST /tasks", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.COMPLETE_TASK:
            tid = extract_task_id(context.message, context)
            data = await self._client.put(f"/tasks/{tid}", json_body={"status": "completed"})
            task = Task(**(data.get("data") or data))
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, task.model_dump())
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, task_id=tid, endpoint=f"PUT /tasks/{tid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.SHOW_TASKS:
            data = await self._client.get("/tasks")
            resp = TaskListResponse(**data)
            tasks = resp.data or []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, endpoint="GET /tasks", task_count=len(tasks), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"tasks": [t.model_dump() for t in tasks]})

        if intent == IntentType.SHOW_OVERDUE:
            data = await self._client.get("/tasks/overdue")
            resp = TaskListResponse(**data)
            tasks = resp.data or []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, endpoint="GET /tasks/overdue", task_count=len(tasks), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"tasks": [t.model_dump() for t in tasks]})

        if intent == IntentType.ASSIGN_TASK:
            tid = extract_task_id(context.message, context)
            assignee = context.metadata.get("assignee", "user")
            data = await self._client.put(f"/tasks/{tid}", json_body={"assignee": assignee})
            task = Task(**(data.get("data") or data))
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"assignee": task.assignee or assignee})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, task_id=tid, assignee=assignee, endpoint=f"PUT /tasks/{tid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.UPDATE_TASK:
            tid = extract_task_id(context.message, context)
            title = extract_task_title(context.message)
            valid, err = validate_not_empty(title, "Task title")
            if not valid:
                return err
            data = await self._client.put(f"/tasks/{tid}", json_body={"title": title})
            task = Task(**(data.get("data") or data))
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, task.model_dump())
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, task_id=tid, title=title, endpoint=f"PUT /tasks/{tid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.CHANGE_DEADLINE:
            tid = extract_task_id(context.message, context)
            due_date = extract_date(context.message) or "2026-07-15"
            data = await self._client.put(f"/tasks/{tid}", json_body={"due_date": due_date})
            task = Task(**(data.get("data") or data))
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"due_date": task.due_date or due_date})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, task_id=tid, due_date=due_date, endpoint=f"PUT /tasks/{tid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.CHANGE_PRIORITY:
            tid = extract_task_id(context.message, context)
            priority = extract_priority(context.message)
            valid, err = validate_priority(priority)
            if not valid:
                return err
            data = await self._client.put(f"/tasks/{tid}", json_body={"priority": priority})
            task = Task(**(data.get("data") or data))
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"priority": task.priority or priority})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, task_id=tid, priority=priority, endpoint=f"PUT /tasks/{tid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.DELETE_TASK:
            tid = extract_task_identifier(context.message)
            if not tid:
                return "I couldn't determine which task you want to delete."
            await self._client.delete(f"/tasks/{tid}")
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": tid})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("TaskTool executed", intent=intent.value, task_id=tid, endpoint=f"DELETE /tasks/{tid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        return "I'm not sure how to handle that request."

    def name(self) -> str:
        return "TaskTool"

    def description(self) -> str:
        return "Manage tasks — create, assign, complete, change deadlines and priority."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "create_task",
            "assign_task",
            "update_task",
            "complete_task",
            "delete_task",
            "change_deadline",
            "change_priority",
            "show_tasks",
            "show_overdue",
        ]
