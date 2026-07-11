from pydantic import BaseModel
from typing import Any


# ── Shared ──────────────────────────────────────────────────────────────────

class StatusResponse(BaseModel):
    status: str
    message: str


# ── Projects ────────────────────────────────────────────────────────────────

class Project(BaseModel):
    id: str
    name: str
    status: str = "active"
    description: str | None = None


class ProjectListResponse(BaseModel):
    status: str
    projects: list[Project]
    message: str | None = None


class ProjectStatusResponse(BaseModel):
    status: str
    project: str
    project_status: str


# ── Tasks ───────────────────────────────────────────────────────────────────

class Task(BaseModel):
    id: str
    title: str
    status: str = "pending"
    due_date: str | None = None
    priority: str | None = None
    assignee: str | None = None


class TaskListResponse(BaseModel):
    status: str
    tasks: list[Task]
    message: str | None = None


# ── Planner / Events ────────────────────────────────────────────────────────

class Event(BaseModel):
    id: str
    title: str
    start: str
    end: str | None = None
    description: str | None = None


class EventListResponse(BaseModel):
    status: str
    events: list[Event]
    message: str | None = None


# ── Notifications ───────────────────────────────────────────────────────────

class Notification(BaseModel):
    id: str
    text: str
    read: bool = False
    created_at: str | None = None


class NotificationListResponse(BaseModel):
    status: str
    notifications: list[Notification]
    message: str | None = None


# ── Dashboard ───────────────────────────────────────────────────────────────

class DashboardData(BaseModel):
    focus: str | None = None
    priorities: list[dict[str, Any]] | None = None
    summary: str | None = None
    risks: list[dict[str, Any]] | None = None


class DashboardResponse(BaseModel):
    status: str
    data: DashboardData | None = None
    message: str | None = None
