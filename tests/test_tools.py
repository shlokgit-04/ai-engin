"""Tests for the tool-calling system.

Verifies:
  - BaseTool contract is honoured by every tool.
  - ToolRouter registers and routes intents correctly.
  - Each tool returns the expected response for every supported action.
  - Tools call BackendClient correctly.
  - Intent classifier maps natural language to the correct IntentType.
  - Orchestrator routes tool intents through ToolRouter instead of agents.
  - GENERAL_CHAT still reaches Gemini (no regression).
"""

import contextlib
import pytest
import json
from typing import Any
from unittest.mock import AsyncMock, patch

from app.orchestrator.enums import IntentType, RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.classifier import Classifier
from app.orchestrator.orchestrator import AIOrchestrator
from app.orchestrator.pipeline import ExecutionPipeline, FEATURE_PLACEHOLDER
from app.tools.base import BaseTool
from app.tools.router import ToolRouter
from app.tools.project_tool import ProjectTool
from app.tools.task_tool import TaskTool
from app.tools.planner_tool import PlannerTool
from app.tools.notification_tool import NotificationTool
from app.tools.dashboard_tool import DashboardTool
from app.tools.executive_tool import ExecutiveTool
from app.models.base import BaseLLM
from app.models.providers.base import ProviderHealth
from app.models.providers.manager import ProviderManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeLLM(BaseLLM):
    async def generate_response(self, prompt: str, **kwargs: Any) -> str:
        return f"fake:{prompt}"

    async def health_check(self) -> bool:
        return True


class FakeKnowledgePipe:
    async def execute(self, context: ExecutionContext) -> str:
        return "Document Intelligence Pipeline not implemented yet."


class _FakeProvider:
    provider_name = "fake"
    current_model = "fake-model"

    async def generate(self, prompt, **kwargs):
        return f"fake:{prompt}"

    async def generate_stream(self, prompt, **kwargs):
        yield f"fake:{prompt}"

    async def health_check(self):
        return ProviderHealth(healthy=True, provider="fake", message="ok")

    def list_models(self):
        return []


def make_context(message: str) -> ExecutionContext:
    return ExecutionContext(message=message)


@pytest.fixture
def pipeline() -> ExecutionPipeline:
    pm = ProviderManager(providers={"fake": _FakeProvider()}, default_provider="fake")
    return ExecutionPipeline(
        provider_manager=pm,
        gemini=FakeLLM(),
        ollama=FakeLLM(),
        knowledge_pipeline=FakeKnowledgePipe(),
    )


@pytest.fixture
def tool_router() -> ToolRouter:
    router = ToolRouter()
    router.register(ExecutiveTool())
    return router


@pytest.fixture
def orchestrator(pipeline: ExecutionPipeline) -> AIOrchestrator:
    router = ToolRouter()
    from app.tools.executive_tool import ExecutiveTool
    router.register(ExecutiveTool())
    return AIOrchestrator(pipeline=pipeline, tool_router=router)


ALL_TOOLS = [
    ProjectTool,
    TaskTool,
    PlannerTool,
    NotificationTool,
    DashboardTool,
    ExecutiveTool,
]


# Actions that have backend endpoints (not fallback-only).
_BACKEND_ACTIONS = {
    "create_project",
    "delete_project",
    "rename_project",
    "show_projects",
    "show_project_status",
    "create_task",
    "assign_task",
    "update_task",
    "complete_task",
    "delete_task",
    "change_deadline",
    "change_priority",
    "show_tasks",
    "show_overdue",
    "add_meeting",
    "cancel_meeting",
    "reschedule_meeting",
    "today_schedule",
    "week_schedule",
    "create_notification",
    "show_notifications",
    "mark_as_read",
    "focus_today",
    "executive_summary",
    "today_priorities",
    "business_risk",
}


# ---------------------------------------------------------------------------
# Fixtures: mock BackendClient so no real HTTP calls happen
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_backend_client():
    """Replace BackendClient with a mock for all tool tests.

    Patches every module that imports BackendClient so that tools
    created anywhere (including inside ToolRouter) use the mock.
    """
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


# ---------------------------------------------------------------------------
# 1.  BaseTool contract
# ---------------------------------------------------------------------------

class TestBaseToolContract:
    """Every tool must honour the BaseTool interface."""

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_inherits_base_tool(self, cls: type) -> None:
        assert issubclass(cls, BaseTool), f"{cls.__name__} does not inherit BaseTool"

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_has_execute(self, cls: type) -> None:
        assert hasattr(cls, "execute")

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_has_name(self, cls: type) -> None:
        assert hasattr(cls, "name")

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_has_description(self, cls: type) -> None:
        assert hasattr(cls, "description")

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_has_supported_actions(self, cls: type) -> None:
        assert hasattr(cls, "supported_actions")

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_supported_actions_returns_list(self, cls: type) -> None:
        actions = cls.supported_actions()
        assert isinstance(actions, list)
        assert len(actions) > 0, f"{cls.__name__} has no supported actions"
        for a in actions:
            assert isinstance(a, str)

    @pytest.mark.parametrize("cls", ALL_TOOLS)
    def test_can_instantiate(self, cls: type) -> None:
        instance = cls()
        assert isinstance(instance, cls)


# ---------------------------------------------------------------------------
# 2.  Tool mock responses
# ---------------------------------------------------------------------------

class TestToolMockResponses:
    """Every supported action must return an executive-style response."""

    # ── Project fallback actions (no backend needed) ─────────────────────

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["assign_member", "remove_member"])
    async def test_project_tool_fallback_actions(self, action: str) -> None:
        tool = ProjectTool()
        intent = IntentType(action)
        result = await tool.execute(make_context("test"), intent)
        assert "successfully" in result.lower()

    # ── Project backend actions ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_project_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Project created."}
        tool = ProjectTool()
        result = await tool.execute(make_context("Create project BuildTrack"), IntentType.CREATE_PROJECT)
        assert "created successfully" in result.lower()
        assert "Project" in result
        assert "BuildTrack" in result

    @pytest.mark.asyncio
    async def test_show_projects_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = []
        tool = ProjectTool()
        result = await tool.execute(make_context("test"), IntentType.SHOW_PROJECTS)
        assert "no projects" in result.lower()

    @pytest.mark.asyncio
    async def test_show_project_status_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "name": "Test", "status": "On Track", "progress": 50, "end_date": "2026-12-31"}]
        tool = ProjectTool()
        result = await tool.execute(make_context("Show project Test"), IntentType.SHOW_PROJECT_STATUS)
        assert "Project:" in result
        assert "Test" in result
        assert "On Track" in result

    @pytest.mark.asyncio
    async def test_delete_project_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "name": "BuildTrack"}]
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Project deleted."}
        tool = ProjectTool()
        result = await tool.execute(make_context("Delete project BuildTrack"), IntentType.DELETE_PROJECT)
        assert "deleted successfully" in result.lower()
        assert "BuildTrack" in result

    @pytest.mark.asyncio
    async def test_rename_project_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "name": "Project"}]
        _mock_backend_client.put.return_value = {"status": "success", "message": "Project renamed."}
        tool = ProjectTool()
        result = await tool.execute(make_context("Rename project Project to NewName"), IntentType.RENAME_PROJECT)
        assert "renamed" in result.lower()

    # ── Task fallback actions ───────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_task_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "API Integration"}]
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Task deleted."}
        tool = TaskTool()
        result = await tool.execute(make_context("Delete task API Integration"), IntentType.DELETE_TASK)
        assert "deleted successfully" in result.lower()
        assert "API Integration" in result

    # ── Task backed actions ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_task_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Task created."}
        tool = TaskTool()
        result = await tool.execute(make_context("test"), IntentType.CREATE_TASK)
        assert "Task created" in result

    @pytest.mark.asyncio
    async def test_assign_task_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.side_effect = [
            [{"id": 1, "title": "Test task"}],
            [{"id": 1, "full_name": "test", "username": "test"}],
        ]
        resp = {"id": 1, "title": "Test task", "assigned_to": {"id": 1, "name": "test"}}
        _mock_backend_client.put.return_value = resp
        tool = TaskTool()
        result = await tool.execute(make_context("Assign task Test task to test"), IntentType.ASSIGN_TASK)
        assert "assigned" in result.lower()

    @pytest.mark.asyncio
    async def test_update_task_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "Test task"}]
        resp = {"id": 1, "title": "Test task"}
        _mock_backend_client.put.return_value = resp
        tool = TaskTool()
        result = await tool.execute(make_context("Update task Test task"), IntentType.UPDATE_TASK)
        assert "updated" in result.lower()

    @pytest.mark.asyncio
    async def test_complete_task_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "Test task"}]
        resp = {"id": 1, "title": "Test task"}
        _mock_backend_client.put.return_value = resp
        tool = TaskTool()
        result = await tool.execute(make_context("Complete task Test task"), IntentType.COMPLETE_TASK)
        assert "completed" in result.lower()

    @pytest.mark.asyncio
    async def test_change_deadline_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "Test"}]
        resp = {"id": 1, "title": "Test", "due_date": "2026-07-15"}
        _mock_backend_client.put.return_value = resp
        tool = TaskTool()
        result = await tool.execute(make_context("Change deadline Test to July 15"), IntentType.CHANGE_DEADLINE)
        assert "Deadline" in result

    @pytest.mark.asyncio
    async def test_change_priority_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "Test"}]
        resp = {"id": 1, "title": "Test", "priority": "high"}
        _mock_backend_client.put.return_value = resp
        tool = TaskTool()
        result = await tool.execute(make_context("Set priority Test to high"), IntentType.CHANGE_PRIORITY)
        assert "Priority" in result

    @pytest.mark.asyncio
    async def test_show_tasks_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = []
        tool = TaskTool()
        result = await tool.execute(make_context("test"), IntentType.SHOW_TASKS)
        assert "no tasks" in result.lower()

    @pytest.mark.asyncio
    async def test_show_overdue_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = []
        tool = TaskTool()
        result = await tool.execute(make_context("test"), IntentType.SHOW_OVERDUE)
        assert "no overdue" in result.lower()

    # ── Planner fallback actions ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_add_reminder_returns_formatted(self) -> None:
        tool = PlannerTool()
        result = await tool.execute(make_context("test"), IntentType.ADD_REMINDER)
        assert "Reminder set" in result

    # ── Planner backed actions ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_add_meeting_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Meeting scheduled."}
        tool = PlannerTool()
        result = await tool.execute(make_context("test"), IntentType.ADD_MEETING)
        assert "Meeting scheduled" in result

    @pytest.mark.asyncio
    async def test_cancel_meeting_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "test meeting"}]
        _mock_backend_client.delete.return_value = {"status": "success", "message": "Meeting cancelled."}
        tool = PlannerTool()
        result = await tool.execute(make_context("Cancel meeting test meeting"), IntentType.CANCEL_MEETING)
        assert "cancelled" in result.lower()

    @pytest.mark.asyncio
    async def test_reschedule_meeting_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "test meeting"}]
        _mock_backend_client.put.return_value = {"status": "success", "message": "Meeting rescheduled."}
        tool = PlannerTool()
        result = await tool.execute(make_context("Reschedule meeting test meeting to tomorrow"), IntentType.RESCHEDULE_MEETING)
        assert "rescheduled" in result.lower()

    @pytest.mark.asyncio
    async def test_today_schedule_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = []
        tool = PlannerTool()
        result = await tool.execute(make_context("test"), IntentType.TODAY_SCHEDULE)
        assert "Today" in result

    @pytest.mark.asyncio
    async def test_week_schedule_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = []
        tool = PlannerTool()
        result = await tool.execute(make_context("test"), IntentType.WEEK_SCHEDULE)
        assert "No events" in result

    # ── Notification backed actions ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_show_notifications_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = []
        tool = NotificationTool()
        result = await tool.execute(make_context("test"), IntentType.SHOW_NOTIFICATIONS)
        assert "no new notifications" in result.lower()

    @pytest.mark.asyncio
    async def test_create_notification_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Notification created."}
        tool = NotificationTool()
        result = await tool.execute(make_context("test"), IntentType.CREATE_NOTIFICATION)
        assert "created successfully" in result.lower()

    @pytest.mark.asyncio
    async def test_mark_as_read_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.put.return_value = {"status": "success", "message": "Notification marked as read."}
        tool = NotificationTool()
        result = await tool.execute(make_context("Mark notification n-123 as read"), IntentType.MARK_AS_READ)
        assert "marked as read" in result.lower()

    # ── Dashboard backed actions (all via GET /dashboard) ───────────────

    @pytest.mark.asyncio
    async def test_focus_today_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "activeProjects": 1,
            "completedProjects": 0,
            "todayTasks": 2,
            "overdueTasks": 0,
            "todayMeetings": 1,
            "highPriorityTasks": 0,
        }
        tool = DashboardTool()
        result = await tool.execute(make_context("test"), IntentType.FOCUS_TODAY)
        assert "Focus for today" in result

    @pytest.mark.asyncio
    async def test_executive_summary_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "activeProjects": 1,
            "completedProjects": 0,
            "todayTasks": 2,
            "overdueTasks": 0,
            "todayMeetings": 1,
            "highPriorityTasks": 0,
        }
        tool = DashboardTool()
        result = await tool.execute(make_context("test"), IntentType.EXECUTIVE_SUMMARY)
        assert "Executive Brief" in result

    @pytest.mark.asyncio
    async def test_today_priorities_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "activeProjects": 0,
            "completedProjects": 0,
            "todayTasks": 0,
            "overdueTasks": 0,
            "todayMeetings": 0,
            "highPriorityTasks": 0,
        }
        tool = DashboardTool()
        result = await tool.execute(make_context("test"), IntentType.TODAY_PRIORITIES)
        assert "Priorities" in result

    @pytest.mark.asyncio
    async def test_business_risk_returns_formatted(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "activeProjects": 0,
            "completedProjects": 0,
            "todayTasks": 0,
            "overdueTasks": 3,
            "todayMeetings": 0,
            "highPriorityTasks": 0,
        }
        tool = DashboardTool()
        result = await tool.execute(make_context("test"), IntentType.BUSINESS_RISK)
        assert "Risk Assessment" in result


# ---------------------------------------------------------------------------
# 3.  ToolRouter
# ---------------------------------------------------------------------------

class TestToolRouter:
    """ToolRouter must correctly route intents to their respective tools."""

    def test_router_constructs(self, tool_router: ToolRouter) -> None:
        assert tool_router is not None

    def test_router_has_all_tools(self, tool_router: ToolRouter) -> None:
        actions = tool_router.list_actions()
        total = sum(len(cls.supported_actions()) for cls in ALL_TOOLS)
        assert len(actions) == total, f"Expected {total} actions, got {len(actions)}"

    def test_route_project_intent(self, tool_router: ToolRouter) -> None:
        tool = tool_router.route(IntentType.CREATE_PROJECT)
        assert isinstance(tool, ProjectTool)

    def test_route_task_intent(self, tool_router: ToolRouter) -> None:
        tool = tool_router.route(IntentType.CREATE_TASK)
        assert isinstance(tool, TaskTool)

    def test_route_planner_intent(self, tool_router: ToolRouter) -> None:
        tool = tool_router.route(IntentType.ADD_MEETING)
        assert isinstance(tool, PlannerTool)

    def test_route_notification_intent(self, tool_router: ToolRouter) -> None:
        tool = tool_router.route(IntentType.CREATE_NOTIFICATION)
        assert isinstance(tool, NotificationTool)

    def test_route_dashboard_intent(self, tool_router: ToolRouter) -> None:
        tool = tool_router.route(IntentType.FOCUS_TODAY)
        assert isinstance(tool, DashboardTool)

    def test_route_general_chat_raises(self, tool_router: ToolRouter) -> None:
        with pytest.raises(ValueError, match="No tool registered"):
            tool_router.route(IntentType.GENERAL_CHAT)

    @pytest.mark.asyncio
    async def test_route_and_execute(self, tool_router: ToolRouter, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Task created."}
        tool = tool_router.route(IntentType.CREATE_TASK)
        result = await tool.execute(make_context("test"), IntentType.CREATE_TASK)
        assert "Task created" in result


# ---------------------------------------------------------------------------
# 4.  Intent classifier
# ---------------------------------------------------------------------------

class TestIntentClassifier:
    """Intent classifier must map natural language to the correct IntentType."""

    classifier = Classifier()

    # --- Project intents ---
    def test_create_project(self):
        assert self.classifier.classify_intent("Create project BuildTrack") == IntentType.CREATE_PROJECT

    def test_show_projects(self):
        assert self.classifier.classify_intent("Show projects") == IntentType.SHOW_PROJECTS

    def test_show_project_status(self):
        assert self.classifier.classify_intent("Project status report") == IntentType.SHOW_PROJECT_STATUS

    def test_assign_member(self):
        assert self.classifier.classify_intent("Assign member to project") == IntentType.ASSIGN_MEMBER

    # --- Task intents ---
    def test_create_task(self):
        assert self.classifier.classify_intent("Create a task") == IntentType.CREATE_TASK

    def test_assign_task(self):
        assert self.classifier.classify_intent("Assign task to Aryan") == IntentType.ASSIGN_TASK

    def test_show_tasks(self):
        assert self.classifier.classify_intent("Show my tasks") == IntentType.SHOW_TASKS
        assert self.classifier.classify_intent("What are my tasks") == IntentType.SHOW_TASKS

    def test_show_overdue(self):
        assert self.classifier.classify_intent("Show overdue tasks") == IntentType.SHOW_OVERDUE

    def test_change_deadline(self):
        assert self.classifier.classify_intent("Set a deadline") == IntentType.CHANGE_DEADLINE

    def test_complete_task(self):
        assert self.classifier.classify_intent("Mark task done") == IntentType.COMPLETE_TASK

    # --- Planner intents ---
    def test_add_meeting(self):
        assert self.classifier.classify_intent("Schedule a meeting") == IntentType.ADD_MEETING

    def test_today_schedule(self):
        assert self.classifier.classify_intent("What is my schedule today") == IntentType.TODAY_SCHEDULE

    def test_week_schedule(self):
        assert self.classifier.classify_intent("What is on my calendar this week") == IntentType.WEEK_SCHEDULE

    def test_add_reminder(self):
        assert self.classifier.classify_intent("Create reminder") == IntentType.ADD_REMINDER

    # --- Notification intents ---
    def test_create_notification(self):
        assert self.classifier.classify_intent("Create notification for deadline") == IntentType.CREATE_NOTIFICATION

    def test_show_notifications(self):
        assert self.classifier.classify_intent("Show notifications") == IntentType.SHOW_NOTIFICATIONS

    # --- Executive / Daily Briefing intents ---
    def test_daily_briefing_good_morning(self):
        assert self.classifier.classify_intent("Good morning") == IntentType.DAILY_BRIEFING

    def test_daily_briefing_start_my_day(self):
        assert self.classifier.classify_intent("Start my day") == IntentType.DAILY_BRIEFING

    def test_daily_briefing_focus(self):
        assert self.classifier.classify_intent("What should I focus on today") == IntentType.DAILY_BRIEFING

    def test_daily_briefing_summary(self):
        assert self.classifier.classify_intent("Today's summary") == IntentType.DAILY_BRIEFING

    # --- Dashboard intents ---
    def test_focus_today(self):
        assert self.classifier.classify_intent("What to focus on") == IntentType.FOCUS_TODAY

    def test_executive_summary(self):
        assert self.classifier.classify_intent("Give me an executive summary") == IntentType.EXECUTIVE_SUMMARY

    def test_today_priorities(self):
        assert self.classifier.classify_intent("What are my priorities today") == IntentType.TODAY_PRIORITIES

    def test_business_risk(self):
        assert self.classifier.classify_intent("What are the business risks") == IntentType.BUSINESS_RISK

    # --- General chat (should remain GENERAL_CHAT) ---
    def test_general_chat(self):
        assert self.classifier.classify_intent("Explain Python") == IntentType.GENERAL_CHAT
        assert self.classifier.classify_intent("Hello") == IntentType.GENERAL_CHAT

    def test_meeting_minutes_not_add_meeting(self):
        """'Create meeting minutes' is a MEETING category request, not ADD_MEETING."""
        assert self.classifier.classify_intent("Create meeting minutes") == IntentType.GENERAL_CHAT
        assert self.classifier.classify_intent("Generate MoM") == IntentType.GENERAL_CHAT


# ---------------------------------------------------------------------------
# 5.  Orchestrator tool routing
# ---------------------------------------------------------------------------

class TestToolRouting:
    """Orchestrator must route tool intents through ToolRouter."""

    @pytest.mark.asyncio
    async def test_create_project_routes_to_project_tool(
        self, orchestrator: AIOrchestrator, _mock_backend_client
    ):
        _mock_backend_client.post.return_value = {"status": "success", "message": "Project created."}
        result = await orchestrator.route_request(make_context("Create project BuildTrack"))
        assert "created successfully" in result

    @pytest.mark.asyncio
    async def test_show_tasks_routes_to_task_tool(
        self, orchestrator: AIOrchestrator, _mock_backend_client
    ):
        _mock_backend_client.get.return_value = []
        result = await orchestrator.route_request(make_context("Show my tasks"))
        assert "no tasks" in result

    @pytest.mark.asyncio
    async def test_schedule_routes_to_planner_tool(
        self, orchestrator: AIOrchestrator, _mock_backend_client
    ):
        _mock_backend_client.post.return_value = {"status": "success", "message": "Meeting scheduled."}
        result = await orchestrator.route_request(make_context("Schedule a meeting"))
        assert "Meeting scheduled" in result

    @pytest.mark.asyncio
    async def test_show_notifications_routes_to_notification_tool(
        self, orchestrator: AIOrchestrator, _mock_backend_client
    ):
        _mock_backend_client.get.return_value = []
        result = await orchestrator.route_request(make_context("Show notifications"))
        assert "notifications" in result.lower()

    @pytest.mark.asyncio
    async def test_daily_briefing_routes_to_executive_tool(
        self, orchestrator: AIOrchestrator, _mock_backend_client
    ):
        _mock_backend_client.get.side_effect = [
            {"activeProjects": 1, "completedProjects": 0, "todayTasks": 1, "overdueTasks": 0, "todayMeetings": 1, "highPriorityTasks": 0},
            [{"id": 1, "title": "Task 1", "status": "pending"}],
            [],
            [{"id": 1, "title": "Standup", "date": "2026-07-11", "start_time": "09:00"}],
            [],
        ]
        result = await orchestrator.route_request(make_context("What should I focus on today"))
        assert "Executive Brief" in result

    @pytest.mark.asyncio
    async def test_general_chat_still_routes_to_gemini(
        self, orchestrator: AIOrchestrator
    ):
        """Regression: GENERAL_CHAT must still reach Gemini."""
        result = await orchestrator.route_request(make_context("Explain Python"))
        assert result.startswith("fake:")


# ---------------------------------------------------------------------------
# 6.  Backend integration: tools call the correct endpoints
# ---------------------------------------------------------------------------

class TestToolBackendIntegration:
    """Each tool action must call the correct backend endpoint."""

    @pytest.mark.asyncio
    async def test_create_project_calls_post_projects(self, _mock_backend_client) -> None:
        tool = ProjectTool()
        await tool.execute(make_context("Create project BuildTrack"), IntentType.CREATE_PROJECT)
        _mock_backend_client.post.assert_called_once_with(
            "/api/v1/projects",
            json_body={"name": "BuildTrack", "description": ""},
            auth_token=None,
        )

    @pytest.mark.asyncio
    async def test_show_projects_calls_get_projects(self, _mock_backend_client) -> None:
        tool = ProjectTool()
        await tool.execute(make_context("Show projects"), IntentType.SHOW_PROJECTS)
        _mock_backend_client.get.assert_called_once_with("/api/v1/projects", auth_token=None)

    @pytest.mark.asyncio
    async def test_create_task_calls_post_tasks(self, _mock_backend_client) -> None:
        tool = TaskTool()
        await tool.execute(make_context("Create task Review API"), IntentType.CREATE_TASK)
        _mock_backend_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_task_calls_put_tasks(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 1, "title": "MyTask"}]
        _mock_backend_client.put.return_value = {"id": 1, "title": "MyTask", "status": "completed"}
        tool = TaskTool()
        await tool.execute(make_context("Complete task MyTask"), IntentType.COMPLETE_TASK)
        _mock_backend_client.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_overdue_calls_get_overdue(self, _mock_backend_client) -> None:
        tool = TaskTool()
        await tool.execute(make_context("Show overdue tasks"), IntentType.SHOW_OVERDUE)
        _mock_backend_client.get.assert_called_once_with("/api/v1/tasks/overdue", auth_token=None)

    @pytest.mark.asyncio
    async def test_add_meeting_calls_post_events(self, _mock_backend_client) -> None:
        _mock_backend_client.post.return_value = {"status": "success", "message": "Meeting scheduled."}
        tool = PlannerTool()
        await tool.execute(make_context("Schedule a meeting"), IntentType.ADD_MEETING)
        _mock_backend_client.post.assert_called_once_with(
            "/api/v1/meetings",
            json_body={"title": "Meeting"},
            auth_token=None,
        )

    @pytest.mark.asyncio
    async def test_today_schedule_calls_get_today(self, _mock_backend_client) -> None:
        tool = PlannerTool()
        await tool.execute(make_context("What is my schedule today"), IntentType.TODAY_SCHEDULE)
        _mock_backend_client.get.assert_called_once_with("/api/v1/meetings", params={"filter": "today"}, auth_token=None)

    @pytest.mark.asyncio
    async def test_show_notifications_calls_get_notifications(self, _mock_backend_client) -> None:
        tool = NotificationTool()
        await tool.execute(make_context("Show notifications"), IntentType.SHOW_NOTIFICATIONS)
        _mock_backend_client.get.assert_called_once_with("/api/v1/notifications", auth_token=None)

    @pytest.mark.asyncio
    async def test_create_notification_calls_post_notifications(self, _mock_backend_client) -> None:
        tool = NotificationTool()
        await tool.execute(make_context("Create notification"), IntentType.CREATE_NOTIFICATION)
        _mock_backend_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_dashboard_calls_get_dashboard(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = {
            "activeProjects": 1,
            "completedProjects": 0,
            "todayTasks": 2,
            "overdueTasks": 0,
            "todayMeetings": 1,
            "highPriorityTasks": 0,
        }
        tool = DashboardTool()
        await tool.execute(make_context("Focus"), IntentType.FOCUS_TODAY)
        _mock_backend_client.get.assert_called_once_with("/api/v1/dashboard/summary", auth_token=None)

    @pytest.mark.asyncio
    async def test_delete_project_calls_delete_projects(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 42, "name": "BuildTrack"}]
        tool = ProjectTool()
        await tool.execute(make_context("Delete project BuildTrack"), IntentType.DELETE_PROJECT)
        _mock_backend_client.delete.assert_called_once_with("/api/v1/projects/42", auth_token=None)

    @pytest.mark.asyncio
    async def test_delete_task_calls_delete_tasks(self, _mock_backend_client) -> None:
        _mock_backend_client.get.return_value = [{"id": 99, "title": "t-123"}]
        tool = TaskTool()
        await tool.execute(make_context("Delete task t-123"), IntentType.DELETE_TASK)
        _mock_backend_client.delete.assert_called_once_with("/api/v1/tasks/99", auth_token=None)

    @pytest.mark.asyncio
    async def test_mark_notification_read_calls_put(self, _mock_backend_client) -> None:
        tool = NotificationTool()
        await tool.execute(make_context("Mark notification n-45 as read"), IntentType.MARK_AS_READ)
        _mock_backend_client.put.assert_called_once_with("/api/v1/notifications/n-45/read", auth_token=None)
