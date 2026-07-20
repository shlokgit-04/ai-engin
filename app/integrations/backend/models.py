from pydantic import BaseModel
from typing import Any


# ── Shared ──────────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Any = None


# ── Projects ────────────────────────────────────────────────────────────────

class Project(BaseModel):
    id: int | str
    name: str
    status: str = "active"
    description: str | None = None


class ProjectListResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: list[Project] = []


# ── Tasks ───────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: int | str
    title: str
    status: str = "pending"
    due_date: str | None = None
    priority: str | None = None
    assignee: str | None = None


class TaskListResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: list[Task] = []


# ── Notifications ───────────────────────────────────────────────────────────

class Notification(BaseModel):
    id: int | str
    title: str = ""
    message: str = ""
    type: str | None = None
    is_read: bool = False
    created_at: str | None = None


class NotificationListResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: list[Notification] = []


# ── Dashboard ───────────────────────────────────────────────────────────────

class DashboardData(BaseModel):
    activeProjects: int = 0
    completedProjects: int = 0
    totalTasks: int = 0
    completedTasks: int = 0
    todayTasks: int = 0
    overdueTasks: int = 0
    todayMeetings: int = 0
    highPriorityTasks: int = 0
    pendingInvitations: int = 0
    meetingsNeedingMOM: int = 0
    pendingApprovals: int = 0
    upcomingDeadlines: int = 0


class DashboardResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: DashboardData | None = None


# ── Events / Planner ───────────────────────────────────────────────────────

class Event(BaseModel):
    id: int | str
    title: str
    start: str = ""
    end: str | None = None
    description: str | None = None


class EventListResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: list[Event] = []


# ── Meetings ─────────────────────────────────────────────────────────────

class Meeting(BaseModel):
    id: int | str
    title: str
    date: str = ""
    start_time: str = ""
    end_time: str | None = None
    status: str = "scheduled"
    analysis_status: str | None = None
    transcript: str | None = None
    ai_summary: str | None = None
    minutes_of_meeting: str | None = None


class MeetingListResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: list[Meeting] = []
