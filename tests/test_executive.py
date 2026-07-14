"""Tests for the Executive Briefing system.

Verifies:
  - PriorityEngine rules for overdue tasks, upcoming meetings, dashboard data.
  - BusinessInsights deterministic rule generation.
  - ExecutiveBriefingService combines 5 backend endpoints into one briefing.
  - ExecutiveTool routes DAILY_BRIEFING to ExecutiveBriefingService.
"""

import pytest
import time
from typing import Any
from unittest.mock import AsyncMock, patch

from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType
from app.executive.priorities import PriorityEngine
from app.executive.insights import BusinessInsights
from app.executive.briefing import ExecutiveBriefingService
from app.tools.executive_tool import ExecutiveTool


def make_context(message: str) -> ExecutionContext:
    return ExecutionContext(message=message)


# ---------------------------------------------------------------------------
# PriorityEngine
# ---------------------------------------------------------------------------

class TestPriorityEngine:
    def setup_method(self) -> None:
        self.engine = PriorityEngine()

    def test_overdue_tasks_take_highest_priority(self) -> None:
        tasks = [{"title": "Task A", "status": "pending"}]
        overdue = [{"title": "Overdue Report", "status": "overdue"}]
        priority = self.engine.determine_priority(tasks, overdue, [])
        assert "Overdue Report" in priority

    def test_overdue_without_titles(self) -> None:
        overdue = [{"status": "overdue"}]
        priority = self.engine.determine_priority([], overdue, [])
        assert "overdue" in priority.lower()

    def test_upcoming_meeting_within_hour(self) -> None:
        with patch("time.localtime", return_value=time.struct_time((2026, 7, 10, 14, 0, 0, 4, 191, 0))):
            events = [{"title": "Sprint Review", "start": "14:30"}]
            priority = self.engine.determine_priority([], [], events)
            assert "Sprint Review" in priority

    def test_no_overdue_or_meeting_uses_dashboard_priorities(self) -> None:
        dashboard = {"priorities": [{"rank": 1, "title": "Finish API design"}]}
        priority = self.engine.determine_priority([], [], [], dashboard)
        assert "Finish API design" in priority

    def test_no_overdue_or_meeting_uses_dashboard_focus(self) -> None:
        dashboard = {"focus": "Review architecture docs"}
        priority = self.engine.determine_priority([], [], [], dashboard)
        assert "Review architecture docs" in priority

    def test_no_overdue_or_meeting_uses_first_task(self) -> None:
        tasks = [{"title": "Fix login bug", "status": "pending"}]
        priority = self.engine.determine_priority(tasks, [], [])
        assert "Fix login bug" in priority

    def test_fallback_when_no_data(self) -> None:
        priority = self.engine.determine_priority([], [], [])
        assert "No priority items identified" in priority

    def test_events_without_valid_time_falls_through(self) -> None:
        events = [{"title": "Meeting", "start": "invalid"}]
        priority = self.engine.determine_priority([], [], events, {"focus": "Write tests"})
        assert "Write tests" in priority


# ---------------------------------------------------------------------------
# BusinessInsights
# ---------------------------------------------------------------------------

class TestBusinessInsights:
    def setup_method(self) -> None:
        self.engine = BusinessInsights()

    def test_overdue_insight_singular(self) -> None:
        insights = self.engine.generate([], [{"title": "Late task"}], [], [], {})
        assert len(insights) >= 1
        assert "1 overdue" in insights[0].lower()

    def test_overdue_insight_plural(self) -> None:
        insights = self.engine.generate([], [{"title": "A"}, {"title": "B"}], [], [], {})
        assert any("2 overdue" in i.lower() for i in insights)

    def test_no_meetings_insight(self) -> None:
        insights = self.engine.generate([], [], [], [], {})
        assert any("No meetings" in i for i in insights)

    def test_manageable_workload(self) -> None:
        tasks = [{"title": "T1", "status": "pending"}, {"title": "T2", "status": "pending"}]
        insights = self.engine.generate(tasks, [], [], [], {})
        assert any("manageable" in i.lower() for i in insights)

    def test_overloaded_workload(self) -> None:
        tasks = [{"title": f"T{i}", "status": "pending"} for i in range(10)]
        insights = self.engine.generate(tasks, [], [], [], {})
        assert any("delegating" in i.lower() or "reprioritising" in i.lower() for i in insights)

    def test_high_risk_insight(self) -> None:
        dashboard = {"risks": [{"level": "high", "description": "Budget risk"}]}
        insights = self.engine.generate([], [], [], [], dashboard)
        assert any("high-risk" in i.lower() for i in insights)

    def test_many_unread_notifications(self) -> None:
        notifications = [{"text": "N1", "read": False} for _ in range(6)]
        insights = self.engine.generate([], [], [], notifications, {})
        assert any("unread" in i.lower() for i in insights)

    def test_no_insights_when_all_quiet(self) -> None:
        insights = self.engine.generate([], [], [{"title": "E1", "start": "10:00"}], [], {})
        assert not insights or all("No meetings" not in i for i in insights)


# ---------------------------------------------------------------------------
# ExecutiveBriefingService
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_backend_client():
    client = AsyncMock()
    client.get = AsyncMock()
    return client


class TestExecutiveBriefingService:
    @pytest.mark.asyncio
    async def test_generate_briefing_combines_all_endpoints(self, mock_backend_client) -> None:
        mock_backend_client.get.side_effect = [
            {"activeProjects": 1, "completedProjects": 0, "todayTasks": 1, "overdueTasks": 0, "todayMeetings": 1, "highPriorityTasks": 0},
            [{"id": 1, "title": "Task 1", "status": "pending"}],
            [],
            [{"id": 1, "title": "Standup", "date": "2026-07-11", "start_time": "09:00", "end_time": "09:15"}],
            [{"id": 1, "title": "Hello", "message": "Hello", "is_read": False}],
        ]
        service = ExecutiveBriefingService(client=mock_backend_client)
        result = await service.generate_briefing()

        assert "Executive Brief" in result
        assert "1 Pending" in result
        assert "1 Scheduled" in result
        assert "1 Unread" in result

    @pytest.mark.asyncio
    async def test_briefing_with_overdue_and_high_risk(self, mock_backend_client) -> None:
        mock_backend_client.get.side_effect = [
            {"activeProjects": 1, "completedProjects": 0, "todayTasks": 1, "overdueTasks": 1, "todayMeetings": 0, "highPriorityTasks": 0},
            [{"id": 1, "title": "Task 1", "status": "pending"}],
            [{"id": 2, "title": "Overdue report", "status": "overdue"}],
            [],
            [],
        ]
        service = ExecutiveBriefingService(client=mock_backend_client)
        result = await service.generate_briefing()

        assert "Medium" in result or "High" in result
        assert "overdue" in result.lower()
        assert "Overdue report" in result

    @pytest.mark.asyncio
    async def test_briefing_empty_all_quiet(self, mock_backend_client) -> None:
        mock_backend_client.get.side_effect = [
            {"activeProjects": 0, "completedProjects": 0, "todayTasks": 0, "overdueTasks": 0, "todayMeetings": 0, "highPriorityTasks": 0},
            [],
            [],
            [],
            [],
        ]
        service = ExecutiveBriefingService(client=mock_backend_client)
        result = await service.generate_briefing()

        assert "Executive Brief" in result
        assert "0 Pending" in result
        assert "0 Overdue" in result
        assert "0 Meetings" in result or "0 Scheduled" in result


# ---------------------------------------------------------------------------
# ExecutiveTool
# ---------------------------------------------------------------------------

class TestExecutiveTool:
    @pytest.mark.asyncio
    async def test_daily_briefing_routes_to_service(self, mock_backend_client) -> None:
        mock_backend_client.get.side_effect = [
            {"activeProjects": 0, "completedProjects": 0, "todayTasks": 0, "overdueTasks": 0, "todayMeetings": 0, "highPriorityTasks": 0},
            [],
            [],
            [],
            [],
        ]
        service = ExecutiveBriefingService(client=mock_backend_client)
        tool = ExecutiveTool(briefing_service=service)
        result = await tool.execute(make_context("Good morning"), IntentType.DAILY_BRIEFING)
        assert "Executive Brief" in result
        assert "0 Pending" in result

    @pytest.mark.asyncio
    async def test_unknown_intent_returns_fallback(self) -> None:
        tool = ExecutiveTool()
        result = await tool.execute(make_context("test"), IntentType.GENERAL_CHAT)
        assert "not sure" in result.lower()

    @pytest.mark.asyncio
    async def test_name_and_description(self) -> None:
        tool = ExecutiveTool()
        assert tool.name() == "ExecutiveTool"
        assert tool.description()
        assert "daily_briefing" in tool.supported_actions()
