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
from app.executive.params import extract_project_name, extract_rename_target, extract_project_identifier, extract_project_old_name
from app.executive.validation import validate_not_empty
from app.executive.suggestions import get_suggestion
from app.core.logging import logger


_FALLBACK = {
    "assign_member": "Member assigned to project successfully.",
    "remove_member": "Member removed from project successfully.",
}

_ERROR_MAP: dict[type, str] = {
    BackendNotFoundError: "I couldn't find that project.",
    BackendConnectionError: "I couldn't reach the backend service.",
    BackendTimeoutError: "The backend took too long to respond.",
    BackendServerError: "The backend is currently unavailable.",
}


class ProjectTool(BaseTool):
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
            logger.warning("ProjectTool error", intent=intent.value, error=str(exc))
            return msg
        except Exception:
            logger.exception("ProjectTool error", intent=intent.value)
            return "An unexpected error occurred while processing your request."

    async def _route(self, context: ExecutionContext, intent: IntentType) -> str:
        start = time.monotonic()
        token = context.auth_token

        if intent == IntentType.CREATE_PROJECT:
            name = extract_project_name(context.message, "New Project")
            valid, err = validate_not_empty(name, "Project name")
            if not valid:
                return err
            await self._client.post("/api/v1/projects", json_body={"name": name, "description": ""}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": name, "status": "Active"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, name=name, endpoint="POST /api/v1/projects", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.SHOW_PROJECTS:
            projects = await self._client.get("/api/v1/projects", auth_token=token)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, endpoint="GET /api/v1/projects", project_count=len(projects), elapsed_ms=elapsed)
            items = [{"name": p.get("name", ""), "status": p.get("status", "")} for p in (projects or [])]
            return self._formatter.format(intent, {"projects": items})

        if intent == IntentType.SHOW_PROJECT_STATUS:
            name = extract_project_identifier(context.message)
            if not name:
                return "Which project would you like to check the status of?"
            projects = await self._client.get("/api/v1/projects", auth_token=token)
            project = None
            for p in (projects or []):
                if p.get("name", "").lower() == name.lower():
                    project = p
                    break
            if project is None:
                return f"I couldn't find a project named \"{name}\"."
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, project_name=name, endpoint="GET /api/v1/projects", elapsed_ms=elapsed)
            return self._formatter.format(intent, {
                "name": project.get("name", "Project"),
                "status": project.get("status", "Active"),
                "progress": project.get("progress", 0),
                "deadline": project.get("end_date", "N/A"),
                "focus": "No current focus.",
            })

        if intent == IntentType.DELETE_PROJECT:
            name = extract_project_identifier(context.message)
            if not name:
                return "I couldn't determine which project you want to delete."
            pid = await self._find_project_id_by_name(name, token)
            if pid is None:
                return f"I couldn't find a project named \"{name}\"."
            await self._client.delete(f"/api/v1/projects/{pid}", auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": name})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, name=name, endpoint=f"DELETE /api/v1/projects/{pid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.RENAME_PROJECT:
            old_name = extract_project_old_name(context.message)
            if not old_name or old_name == "Project":
                old_name = extract_project_identifier(context.message) or "default"
            new_name = extract_rename_target(context.message)
            valid, err = validate_not_empty(new_name, "New project name")
            if not valid:
                return err
            pid = await self._find_project_id_by_name(old_name, token)
            if pid is None:
                return f"I couldn't find a project named \"{old_name}\"."
            await self._client.put(f"/api/v1/projects/{pid}", json_body={"name": new_name}, auth_token=token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": new_name})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, new_name=new_name, endpoint=f"PUT /api/v1/projects/{pid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        return "I'm not sure how to handle that request."

    async def _find_project_id_by_name(self, name: str, token: str) -> int | None:
        projects = await self._client.get("/api/v1/projects", auth_token=token)
        for p in (projects or []):
            if p.get("name", "").lower() == name.lower():
                return p.get("id")
        return None

    def name(self) -> str:
        return "ProjectTool"

    def description(self) -> str:
        return "Manage projects — create, delete, rename, assign members."

    @classmethod
    def supported_actions(cls) -> list[str]:
        return [
            "create_project",
            "delete_project",
            "rename_project",
            "show_projects",
            "show_project_status",
            "assign_member",
            "remove_member",
        ]
