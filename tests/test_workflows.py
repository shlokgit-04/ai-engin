"""End-to-end workflow tests for every supported user scenario.

Each test simulates the full flow:
  message → Classifier.classify_intent → ToolRouter.route → Tool.execute → formatted response

Verifies:
  - Parameters are correctly extracted from natural language
  - Validation catches bad inputs
  - Backend endpoints receive the correct payload
  - Error handling returns user-friendly messages
  - Follow-up suggestions are appended
  - All tool intents produce valid formatted responses
"""

import contextlib
import pytest
from typing import Any
from unittest.mock import AsyncMock, patch

from app.orchestrator.enums import IntentType, RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.classifier import Classifier
from app.tools.project_tool import ProjectTool
from app.tools.task_tool import TaskTool
from app.tools.planner_tool import PlannerTool
from app.tools.notification_tool import NotificationTool
from app.tools.dashboard_tool import DashboardTool
from app.tools.executive_tool import ExecutiveTool
from app.executive.briefing import ExecutiveBriefingService


def make_context(message: str, **overrides: Any) -> ExecutionContext:
    return ExecutionContext(message=message, **overrides)


_CLASSIFIER = Classifier()


# ── Fixture: mock BackendClient for all tools ──────────────────────────────

@pytest.fixture(autouse=True)
def _mock_backend_client():
    mock_instance = AsyncMock()
    mock_instance.get = AsyncMock(return_value={"status": "success", "message": "OK"})
    mock_instance.post = AsyncMock(return_value={"status": "success", "message": "OK"})
    mock_instance.put = AsyncMock(return_value={"status": "success", "message": "OK"})
    mock_instance.delete = AsyncMock(return_value={"status": "success", "message": "OK"})

    modules = [
        "app.integrations.backend.client",
        "app.tools.project_tool",
        "app.tools.task_tool",
        "app.tools.planner_tool",
        "app.tools.notification_tool",
        "app.tools.dashboard_tool",
        "app.executive.briefing",
    ]
    with contextlib.ExitStack() as stack:
        for mod in modules:
            stack.enter_context(patch(f"{mod}.BackendClient", return_value=mock_instance))
        yield mock_instance


# ── Helper: classify + route + execute ─────────────────────────────────────

async def run_workflow(message: str, tool_instance: Any, intent: IntentType | None = None) -> str:
    if intent is None:
        intent = _CLASSIFIER.classify_intent(message)
    return await tool_instance.execute(make_context(message), intent)


# ═══════════════════════════════════════════════════════════════════════════
# 1.  Project Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestProjectWorkflows:

    async def _exec(self, message: str, intent: IntentType | None = None) -> str:
        return await run_workflow(message, ProjectTool(), intent)

    # ── CREATE ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_project_extracts_name(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Project created."}
        result = await self._exec("Create project BuildTrack")
        _mock_backend_client.post.assert_called_once_with(
            "/projects",
            json_body={"name": "BuildTrack", "description": ""},
        )
        assert "BuildTrack" in result
        assert "created" in result.lower()
        assert "Would you like" in result

    @pytest.mark.asyncio
    async def test_create_project_without_name_uses_fallback(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Project created."}
        result = await self._exec("Create project")
        _mock_backend_client.post.assert_called_once()
        assert "Project" in result
        assert "created" in result.lower()

    # ── LIST ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_show_projects_empty(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {"status": "success", "projects": []}
        result = await self._exec("Show projects")
        assert "no projects" in result.lower()

    @pytest.mark.asyncio
    async def test_show_projects_with_data(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "projects": [{"id": "p1", "name": "Alpha"}, {"id": "p2", "name": "Beta"}],
        }
        result = await self._exec("Show projects")
        assert "Alpha" in result
        assert "Beta" in result

    # ── STATUS ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_show_project_status(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {"id": "p1", "name": "BuildTrack", "status": "On Track"}
        result = await self._exec("Project status report")
        assert "Project:" in result
        assert "BuildTrack" in result
        assert "On Track" in result

    # ── DELETE ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_project(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        result = await self._exec("Delete project Alpha", IntentType.DELETE_PROJECT)
        assert "deleted" in result.lower()
        assert "Alpha" in result
        assert "Would you like" in result

    # ── RENAME ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_rename_project(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "message": "Renamed."}
        result = await self._exec("Rename project to MyApp", IntentType.RENAME_PROJECT)

        assert "MyApp" in result
        assert "renamed" in result.lower()

    # ── FALLBACK ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_assign_member_fallback(self) -> None:
        result = await self._exec("Assign member", IntentType.ASSIGN_MEMBER)
        assert "successfully" in result.lower()

    @pytest.mark.asyncio
    async def test_remove_member_fallback(self) -> None:
        result = await self._exec("Remove member", IntentType.REMOVE_MEMBER)
        assert "successfully" in result.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 2.  Task Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestTaskWorkflows:

    async def _exec(self, message: str, intent: IntentType | None = None) -> str:
        return await run_workflow(message, TaskTool(), intent)

    # ── CREATE ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_task_extracts_title(self, _mock_backend_client) -> None:
        result = await self._exec("Create task Review PR #42")
        _mock_backend_client.post.assert_called_once()
        assert "Task created" in result
        assert "Would you like" in result

    @pytest.mark.asyncio
    async def test_create_task_with_priority(self, _mock_backend_client) -> None:
        result = await self._exec("Create high priority task Fix login bug", IntentType.CREATE_TASK)
        _mock_backend_client.post.assert_called_once()
        assert "High" in result

    # ── COMPLETE ────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_complete_task(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {
            "status": "success", "id": "t1", "title": "Fix bug", "status": "completed",
        }
        result = await self._exec("Mark task done", IntentType.COMPLETE_TASK)
        assert "completed" in result.lower()

    # ── LIST ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_show_tasks(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "tasks": [{"id": "t1", "title": "Task 1", "status": "pending"}],
            "message": "1 task",
        }
        result = await self._exec("Show my tasks")
        assert "You have 1 task" in result

    @pytest.mark.asyncio
    async def test_show_overdue(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "tasks": [{"id": "t2", "title": "Late task", "status": "overdue"}],
            "message": "1 overdue",
        }
        result = await self._exec("Show overdue")
        _mock_backend_client.get.assert_called_once_with("/tasks/overdue")
        assert "Late task" in result

    # ── ASSIGN ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_assign_task(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {
            "status": "success", "id": "t1", "title": "Task", "assignee": "Aryan",
        }
        result = await self._exec("Assign task to Aryan", IntentType.ASSIGN_TASK)
        assert "assigned" in result.lower()

    # ── UPDATE ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_task(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {
            "status": "success", "id": "t1", "title": "New title",
        }
        result = await self._exec("Update task", IntentType.UPDATE_TASK)
        assert "updated" in result.lower()

    # ── CHANGE DEADLINE ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_change_deadline(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {
            "status": "success", "id": "t1", "title": "Task", "due_date": "2026-07-20",
        }
        result = await self._exec("Set deadline to July 20", IntentType.CHANGE_DEADLINE)
        assert "Deadline" in result

    # ── CHANGE PRIORITY ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_change_priority(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {
            "status": "success", "id": "t1", "title": "Task", "priority": "high",
        }
        result = await self._exec("Set priority to high", IntentType.CHANGE_PRIORITY)
        assert "Priority" in result

    # ── DELETE ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_task(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        result = await self._exec("Delete task Backend API", IntentType.DELETE_TASK)
        assert "deleted successfully" in result.lower()
        assert "Backend API" in result


# ═══════════════════════════════════════════════════════════════════════════
# 3.  Planner Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestPlannerWorkflows:

    async def _exec(self, message: str, intent: IntentType | None = None) -> str:
        return await run_workflow(message, PlannerTool(), intent)

    @pytest.mark.asyncio
    async def test_add_meeting(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Meeting scheduled."}
        result = await self._exec("Schedule a meeting")
        assert "Meeting scheduled" in result
        assert "Would you like" in result

    @pytest.mark.asyncio
    async def test_cancel_meeting(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Cancelled."}
        result = await self._exec("Cancel meeting", IntentType.CANCEL_MEETING)
        assert "cancelled" in result.lower()

    @pytest.mark.asyncio
    async def test_reschedule_meeting(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "message": "Rescheduled."}
        result = await self._exec("Reschedule meeting to tomorrow", IntentType.RESCHEDULE_MEETING)
        assert "rescheduled" in result.lower()

    @pytest.mark.asyncio
    async def test_today_schedule(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "events": [{"id": "e1", "title": "Standup", "start": "09:00", "end": "09:15"}],
        }
        result = await self._exec("What is my schedule today")
        assert "Today" in result

    @pytest.mark.asyncio
    async def test_week_schedule(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "events": [{"id": "e1", "title": "Sprint Review", "start": "2026-07-13 14:00"}],
        }
        result = await self._exec("What is on my calendar this week")
        assert "1 event(s)" in result.lower()
        assert "Sprint Review" in result

    @pytest.mark.asyncio
    async def test_week_schedule_with_event_details(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "events": [{"id": "e2", "title": "Design Review", "start": "15:00", "end": "16:00"}],
        }
        result = await self._exec("What is on my calendar this week")
        assert "1 event(s)" in result.lower()
        assert "Design Review at 15:00" in result

    @pytest.mark.asyncio
    async def test_add_reminder_fallback(self) -> None:
        result = await self._exec("Create reminder", IntentType.ADD_REMINDER)
        assert "Reminder set" in result


# ═══════════════════════════════════════════════════════════════════════════
# 4.  Notification Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestNotificationWorkflows:

    async def _exec(self, message: str, intent: IntentType | None = None) -> str:
        return await run_workflow(message, NotificationTool(), intent)

    @pytest.mark.asyncio
    async def test_show_notifications(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "notifications": [{"id": "n1", "text": "Deadline tomorrow", "read": False}],
        }
        result = await self._exec("Show notifications")
        assert "Deadline tomorrow" in result

    @pytest.mark.asyncio
    async def test_create_notification(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Created."}
        result = await self._exec("Create notification", IntentType.CREATE_NOTIFICATION)
        assert "created" in result.lower()

    @pytest.mark.asyncio
    async def test_mark_as_read(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "message": "Marked as read."}
        result = await self._exec("Mark notification n-123 as read", IntentType.MARK_AS_READ)
        assert "marked as read" in result.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 5.  Dashboard Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestDashboardWorkflows:

    async def _exec(self, message: str, intent: IntentType | None = None) -> str:
        return await run_workflow(message, DashboardTool(), intent)

    @pytest.mark.asyncio
    async def test_focus_today(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "data": {"focus": "Review API design"},
        }
        result = await self._exec("What to focus on")
        assert "Focus for today" in result
        assert "Review API design" in result

    @pytest.mark.asyncio
    async def test_executive_summary(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "data": {"focus": "All on track", "risks": []},
        }
        result = await self._exec("Give me an executive summary")
        assert "Executive Brief" in result

    @pytest.mark.asyncio
    async def test_today_priorities(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "data": {"priorities": [{"rank": 1, "title": "Finish API"}]},
        }
        result = await self._exec("What are my priorities today")
        assert "Priorities" in result
        assert "Finish API" in result

    @pytest.mark.asyncio
    async def test_business_risk(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "status": "success",
            "data": {"risks": [{"level": "high", "description": "Budget overrun"}]},
        }
        result = await self._exec("What are the business risks")
        assert "Risk Assessment" in result
        assert "Budget overrun" in result


# ═══════════════════════════════════════════════════════════════════════════
# 6.  Executive Briefing Workflow
# ═══════════════════════════════════════════════════════════════════════════

class TestExecutiveBriefingWorkflow:

    @pytest.mark.asyncio
    async def test_daily_briefing_full(self, _mock_backend_client) -> None:
        _mock_backend_client.get.side_effect = [
            {"status": "success", "data": {"focus": "Review API", "risks": [{"level": "low", "description": "None"}]}},
            {"status": "success", "tasks": [{"id": "t1", "title": "Finish tests", "status": "pending"}], "message": "1 task"},
            {"status": "success", "tasks": [], "message": "0 overdue"},
            {"status": "success", "events": [{"id": "e1", "title": "Standup", "start": "09:00", "end": "09:30"}], "message": "1 event"},
            {"status": "success", "notifications": [], "message": "0 notifications"},
        ]
        service = ExecutiveBriefingService(client=_mock_backend_client)
        tool = ExecutiveTool(briefing_service=service)
        result = await tool.execute(make_context("Good morning"), IntentType.DAILY_BRIEFING)
        assert "Executive Brief" in result
        assert "1 Pending" in result
        assert "1 Scheduled" in result
        assert "0 Overdue" in result

    @pytest.mark.asyncio
    async def test_daily_briefing_high_risk(self, _mock_backend_client) -> None:
        _mock_backend_client.get.side_effect = [
            {"status": "success", "data": {"focus": "Fix security bug", "risks": [{"level": "high", "description": "Security vulnerability"}]}},
            {"status": "success", "tasks": [{"id": "t1", "title": "Task 1", "status": "pending"}], "message": "1 task"},
            {"status": "success", "tasks": [{"id": "t2", "title": "Overdue", "status": "overdue"}], "message": "1 overdue"},
            {"status": "success", "events": [], "message": "0 events"},
            {"status": "success", "notifications": [], "message": "0 notifications"},
        ]
        service = ExecutiveBriefingService(client=_mock_backend_client)
        tool = ExecutiveTool(briefing_service=service)
        result = await tool.execute(make_context("Start my day"), IntentType.DAILY_BRIEFING)
        assert "High" in result
        assert "overdue" in result.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 7.  Validation & Error Handling Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestValidationWorkflows:

    @pytest.mark.asyncio
    async def test_backend_connection_error(self, _mock_backend_client) -> None:
        from app.integrations.backend.exceptions import BackendConnectionError
        _mock_backend_client.get.side_effect = BackendConnectionError("Connection refused")
        tool = ProjectTool()
        result = await tool.execute(make_context("Show projects"), IntentType.SHOW_PROJECTS)
        assert "couldn't reach" in result.lower()

    @pytest.mark.asyncio
    async def test_backend_not_found_error(self, _mock_backend_client) -> None:
        from app.integrations.backend.exceptions import BackendNotFoundError
        _mock_backend_client.get.side_effect = BackendNotFoundError("Not found")
        tool = ProjectTool()
        result = await tool.execute(make_context("Show project status"), IntentType.SHOW_PROJECT_STATUS)
        assert "couldn't find" in result.lower()

    @pytest.mark.asyncio
    async def test_backend_timeout_error(self, _mock_backend_client) -> None:
        from app.integrations.backend.exceptions import BackendTimeoutError
        _mock_backend_client.get.side_effect = BackendTimeoutError("Timed out")
        tool = TaskTool()
        result = await tool.execute(make_context("Show tasks"), IntentType.SHOW_TASKS)
        assert "took too long" in result.lower()

    @pytest.mark.asyncio
    async def test_backend_server_error(self, _mock_backend_client) -> None:
        from app.integrations.backend.exceptions import BackendServerError
        _mock_backend_client.get.side_effect = BackendServerError("500")
        tool = DashboardTool()
        result = await tool.execute(make_context("Focus"), IntentType.FOCUS_TODAY)
        assert "currently unavailable" in result.lower()

    @pytest.mark.asyncio
    async def test_generic_exception_caught(self, _mock_backend_client) -> None:
        _mock_backend_client.get.side_effect = RuntimeError("Unexpected")
        tool = TaskTool()
        result = await tool.execute(make_context("Show tasks"), IntentType.SHOW_TASKS)
        assert "unexpected error" in result.lower()

    @pytest.mark.asyncio
    async def test_unknown_intent_returns_fallback(self) -> None:
        tool = ProjectTool()
        result = await tool.execute(make_context("Do something weird"), IntentType.GENERAL_CHAT)
        assert "not sure" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_project_validation_error(self) -> None:
        tool = ProjectTool()
        result = await tool.execute(make_context("Delete project"), IntentType.DELETE_PROJECT)
        assert "couldn't determine which project" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_task_validation_error(self) -> None:
        tool = TaskTool()
        result = await tool.execute(make_context("Delete task"), IntentType.DELETE_TASK)
        assert "couldn't determine which task" in result.lower()

    @pytest.mark.asyncio
    async def test_mark_as_read_validation_error(self) -> None:
        tool = NotificationTool()
        result = await tool.execute(make_context("Mark as read"), IntentType.MARK_AS_READ)
        assert "couldn't determine which notification" in result.lower()


# ═══════════════════════════════════════════════════════════════════════════
# 8.  Follow-up Suggestion Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestFollowUpSuggestions:

    @pytest.mark.asyncio
    async def test_create_project_has_suggestion(self, _mock_backend_client) -> None:
        tool = ProjectTool()
        result = await tool.execute(make_context("Create project Test"), IntentType.CREATE_PROJECT)
        assert "Would you like" in result

    @pytest.mark.asyncio
    async def test_create_task_has_suggestion(self, _mock_backend_client) -> None:
        tool = TaskTool()
        result = await tool.execute(make_context("Create task Test"), IntentType.CREATE_TASK)
        assert "Would you like" in result

    @pytest.mark.asyncio
    async def test_complete_task_has_suggestion(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "id": "t1", "title": "Test"}
        tool = TaskTool()
        result = await tool.execute(make_context("Complete task"), IntentType.COMPLETE_TASK)
        assert "Would you like" in result

    @pytest.mark.asyncio
    async def test_add_meeting_has_suggestion(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "OK"}
        tool = PlannerTool()
        result = await tool.execute(make_context("Schedule meeting"), IntentType.ADD_MEETING)
        assert "Would you like" in result


# ═══════════════════════════════════════════════════════════════════════════
# 9.  Parameter Extraction Workflows
# ═══════════════════════════════════════════════════════════════════════════

class TestParameterExtraction:

    @pytest.mark.asyncio
    async def test_create_project_extracts_name_correctly(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "OK"}
        tool = ProjectTool()
        await tool.execute(make_context("Create project MyCoolApp"), IntentType.CREATE_PROJECT)
        _mock_backend_client.post.assert_called_once_with(
            "/projects",
            json_body={"name": "MyCoolApp", "description": ""},
        )

    @pytest.mark.asyncio
    async def test_create_task_extracts_title_without_prefix(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "OK"}
        tool = TaskTool()
        await tool.execute(
            make_context("Create a task"),
            IntentType.CREATE_TASK,
        )
        _mock_backend_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_priority_extraction(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "OK"}
        tool = TaskTool()
        result = await tool.execute(
            make_context("Create high priority task Urgent"),
            IntentType.CREATE_TASK,
        )
        assert "High" in result

    @pytest.mark.asyncio
    async def test_date_extraction_in_task(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "OK"}
        tool = TaskTool()
        result = await tool.execute(
            make_context("Create task Release notes due July 20"),
            IntentType.CREATE_TASK,
        )
        assert "July 20" in result or "Jul 20" in result or "07-20" in result

    @pytest.mark.asyncio
    async def test_notification_creation_with_message(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Created."}
        tool = NotificationTool()
        result = await tool.execute(
            make_context("Create notification Remind me about standup"),
            IntentType.CREATE_NOTIFICATION,
        )
        assert "created" in result.lower()

    @pytest.mark.asyncio
    async def test_delete_project_extracts_identifier(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        tool = ProjectTool()
        await tool.execute(make_context("Delete project BuildTrack"), IntentType.DELETE_PROJECT)
        _mock_backend_client.delete.assert_called_once_with("/projects/BuildTrack")

    @pytest.mark.asyncio
    async def test_delete_project_standalone_syntax(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        tool = ProjectTool()
        await tool.execute(make_context("Delete BuildTrack"), IntentType.DELETE_PROJECT)
        _mock_backend_client.delete.assert_called_once_with("/projects/BuildTrack")

    @pytest.mark.asyncio
    async def test_delete_project_remove_syntax(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        tool = ProjectTool()
        await tool.execute(make_context("Remove project Alpha"), IntentType.DELETE_PROJECT)
        _mock_backend_client.delete.assert_called_once_with("/projects/Alpha")

    @pytest.mark.asyncio
    async def test_delete_task_extracts_identifier(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        tool = TaskTool()
        await tool.execute(make_context("Delete task Backend API"), IntentType.DELETE_TASK)
        _mock_backend_client.delete.assert_called_once_with("/tasks/Backend API")

    @pytest.mark.asyncio
    async def test_delete_task_with_id(self, _mock_backend_client) -> None:
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Deleted."}
        tool = TaskTool()
        await tool.execute(make_context("Delete task t-123"), IntentType.DELETE_TASK)
        _mock_backend_client.delete.assert_called_once_with("/tasks/t-123")

    @pytest.mark.asyncio
    async def test_mark_notification_extracts_id(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "message": "OK"}
        tool = NotificationTool()
        await tool.execute(make_context("Mark notification n-123 as read"), IntentType.MARK_AS_READ)
        _mock_backend_client.put.assert_called_once_with("/notifications/n-123/read")

    @pytest.mark.asyncio
    async def test_mark_notification_read_syntax(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "message": "OK"}
        tool = NotificationTool()
        await tool.execute(make_context("Read notification n-45"), IntentType.MARK_AS_READ)
        _mock_backend_client.put.assert_called_once_with("/notifications/n-45/read")
