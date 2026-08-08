import time
import re

from app.tools.base import BaseTool
from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.integrations.backend.client import BackendClient
from app.integrations.backend.models import Project, ProjectListResponse, APIResponse
from app.integrations.backend.exceptions import (
    BackendNotFoundError,
    BackendConnectionError,
    BackendTimeoutError,
    BackendServerError,
)
from app.response.formatter import ResponseFormatter
from app.executive.params import extract_project_name, extract_rename_target, extract_project_identifier
from app.executive.validation import validate_not_empty
from app.executive.users import match_user
from app.executive.suggestions import get_suggestion
from app.core.logging import logger


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
        logger.info("ProjectTool executing", intent=intent.value, input=context.message[:200])
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

        if intent == IntentType.CREATE_PROJECT:
            name = extract_project_name(context.message, "New Project")
            valid, err = validate_not_empty(name, "Project name")
            if not valid:
                return err
            data = await self._client.post("/projects", json_body={"name": name, "description": ""}, auth_token=context.user_auth_token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": name, "status": "Active"})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, name=name, endpoint="POST /projects", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.SHOW_PROJECTS:
            data = await self._client.get("/projects", auth_token=context.user_auth_token)
            resp = ProjectListResponse(**data)
            projects = resp.data or []
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, endpoint="GET /projects", project_count=len(projects), elapsed_ms=elapsed)
            return self._formatter.format(intent, {"projects": [p.model_dump() for p in projects]})

        if intent == IntentType.SHOW_PROJECT_STATUS:
            pid = context.project_id or "default"
            data = await self._client.get(f"/projects/{pid}", auth_token=context.user_auth_token)
            project = Project(**data)
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, project_id=pid, endpoint=f"GET /projects/{pid}", elapsed_ms=elapsed)
            return self._formatter.format(intent, project.model_dump())

        if intent == IntentType.DELETE_PROJECT:
            pid = extract_project_identifier(context.message)
            if not pid:
                return "I couldn't determine which project you want to delete."
            name = pid
            await self._client.delete(f"/projects/{pid}", auth_token=context.user_auth_token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": name})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, name=name, endpoint=f"DELETE /projects/{pid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.RENAME_PROJECT:
            pid = context.project_id or "default"
            new_name = extract_rename_target(context.message)
            valid, err = validate_not_empty(new_name, "New project name")
            if not valid:
                return err
            data = await self._client.put(f"/projects/{pid}", json_body={"name": new_name}, auth_token=context.user_auth_token)
            suggestion = get_suggestion(intent.value)
            result = self._formatter.format(intent, {"name": new_name})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info("ProjectTool executed", intent=intent.value, new_name=new_name, endpoint=f"PUT /projects/{pid}", elapsed_ms=elapsed)
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.ASSIGN_MEMBER:
            pid = context.project_id
            member_name = context.metadata.get("member_name") or context.metadata.get("assignee", "")
            if not member_name:
                member_name = self._extract_member_name(context.message)
            if not member_name:
                return "Who would you like to add as a member? Please include the member's name."
            if not pid:
                projects_data = await self._client.get("/projects", auth_token=context.user_auth_token)
                projects_resp = ProjectListResponse(**projects_data)
                projects = projects_resp.data or []
                msg_lower = context.message.lower()
                matched = None
                for p in projects:
                    if p.name.lower() in msg_lower:
                        matched = p
                        break
                if not matched:
                    return "I couldn't find which project to add the member to. Please mention the project name."
                pid = str(matched.id)
            users_data = await self._client.get("/users", auth_token=context.user_auth_token)
            users_resp = APIResponse(**users_data)
            users = users_resp.data or []
            matched_user = match_user(users, member_name)
            if not matched_user:
                return f"I couldn't find a team member named '{member_name}'. Please check the name and try again."
            user_id = matched_user.get("id")
            resp = await self._client.post(f"/projects/{pid}/members/{user_id}", auth_token=context.user_auth_token)
            suggestion = get_suggestion(intent.value)
            user_display = matched_user.get("full_name") or matched_user.get("name", "user")
            result = self._formatter.format(intent, {"project_name": pid, "user_name": user_display})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "ProjectTool executed",
                intent=intent.value,
                project_id=pid,
                user_id=user_id,
                member=member_name,
                request={"user_id": user_id},
                response_status=resp.get("status") or resp.get("success"),
                endpoint=f"POST /projects/{pid}/members/{user_id}",
                elapsed_ms=elapsed,
            )
            return f"{result}\n\n{suggestion}"

        if intent == IntentType.REMOVE_MEMBER:
            pid = context.project_id
            member_name = context.metadata.get("member_name") or context.metadata.get("assignee", "")
            if not member_name:
                member_name = self._extract_member_name(context.message)
            if not member_name:
                return "Who would you like to remove from the project? Please include the member's name."
            if not pid:
                projects_data = await self._client.get("/projects", auth_token=context.user_auth_token)
                projects_resp = ProjectListResponse(**projects_data)
                projects = projects_resp.data or []
                msg_lower = context.message.lower()
                matched = None
                for p in projects:
                    if p.name.lower() in msg_lower:
                        matched = p
                        break
                if not matched:
                    return "I couldn't find which project to remove the member from. Please mention the project name."
                pid = str(matched.id)
            users_data = await self._client.get("/users", auth_token=context.user_auth_token)
            users_resp = APIResponse(**users_data)
            users = users_resp.data or []
            matched_user = match_user(users, member_name)
            if not matched_user:
                return f"I couldn't find a team member named '{member_name}'. Please check the name and try again."
            user_id = matched_user.get("id")
            resp = await self._client.delete(f"/projects/{pid}/members/{user_id}", auth_token=context.user_auth_token)
            suggestion = get_suggestion(intent.value)
            user_display = matched_user.get("full_name") or matched_user.get("name", "user")
            result = self._formatter.format(intent, {"project_name": pid, "user_name": user_display})
            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "ProjectTool executed",
                intent=intent.value,
                project_id=pid,
                user_id=user_id,
                member=member_name,
                response_status=resp.get("status") or resp.get("success"),
                endpoint=f"DELETE /projects/{pid}/members/{user_id}",
                elapsed_ms=elapsed,
            )
            return f"{result}\n\n{suggestion}"

        return "I'm not sure how to handle that request."

    def name(self) -> str:
        return "ProjectTool"

    def _extract_member_name(self, message: str) -> str:
        """Fallback: pull a person's name from 'add X to project' / 'assign member X' text."""
        lower = message.lower()
        for pattern in (
            r"(?:add|assign|remove|invite)\s+member\s+(\S+)",
            r"(?:add|assign|remove|invite)\s+(\S+)\s+(?:to|from)\s+(?:the\s+)?(?:project|team)",
            r"(?:add|assign|remove|invite)\s+(\S+)\s+as\s+(?:a\s+)?member",
        ):
            m = re.search(pattern, lower)
            if m:
                name = m.group(1).strip(".,!?@")
                if name and name.lower() not in {"the", "a", "an", "to", "from", "project", "member"}:
                    return name.capitalize()
        return ""

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
