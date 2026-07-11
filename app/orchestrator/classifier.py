import re

from app.orchestrator.enums import RequestCategory, IntentType


_IMAGE_EXT = re.compile(r"\.(png|jpg|jpeg)\b", re.IGNORECASE)
_DOC_EXT = re.compile(r"\.(pdf|docx?)\b", re.IGNORECASE)

_IMAGE_KEYWORDS = {"image", "picture", "photo", "analyze image", "upload image"}
_DOC_QUERY_KEYWORDS = {
    "summarize", "summarise", "search document", "find contract",
    "extract from document", "document query", "find in document",
}
_DOC_UPLOAD_KEYWORDS = {
    "upload document", "upload file", "upload pdf", "upload doc",
    "attach file", "upload", "pdf", "docx",
}
_MEETING_KEYWORDS = {"minutes", "mom", "meeting", "transcript", "meeting notes", "agenda"}
_TASK_KEYWORDS = {"task", "deadline", "reminder", "todo", "to-do", "assign", "follow-up"}
_COMPANY_KEYWORDS = {
    "nurofin", "vendor", "project", "employee", "finance",
    "agreement", "customer", "proposal", "policy", "internal",
    "meeting notes", "company", "hr", "payroll", "contract",
    "revenue", "quarterly", "board", "expense", "budget",
    "invoice", "purchase order", "po", "sow", "statement of work",
    "ndp", "nda", "non-disclosure", "sla", "kpi",
    "department", "team", "headcount", "hiring", "onboarding",
    "salary", "compensation", "benefits", "insurance",
    "audit", "compliance", "regulation", "approval",
    "submission", "nuro", "mou", "confidential",
}


class Classifier:
    def classify(self, message: str) -> RequestCategory:
        lower = message.lower()

        if _IMAGE_EXT.search(lower) or any(k in lower for k in _IMAGE_KEYWORDS):
            return RequestCategory.IMAGE_ANALYSIS

        if any(k in lower for k in _DOC_QUERY_KEYWORDS):
            return RequestCategory.DOCUMENT_QUERY

        if _DOC_EXT.search(lower) or any(k in lower for k in _DOC_UPLOAD_KEYWORDS):
            return RequestCategory.DOCUMENT_UPLOAD

        if any(k in lower for k in _MEETING_KEYWORDS):
            return RequestCategory.MEETING

        if any(k in lower for k in _TASK_KEYWORDS):
            return RequestCategory.TASK_ASSISTANT

        if any(k in lower for k in _COMPANY_KEYWORDS):
            return RequestCategory.COMPANY_KNOWLEDGE

        return RequestCategory.GENERAL_CHAT

    def classify_intent(self, message: str) -> IntentType:
        lower = message.lower()

        # --- Project intents ---
        if _triggered(lower, ["create project", "start project", "new project", "build project", "create a project"]):
            return IntentType.CREATE_PROJECT
        if _triggered(lower, ["delete project", "remove project"]):
            return IntentType.DELETE_PROJECT
        if _triggered(lower, ["rename project"]):
            return IntentType.RENAME_PROJECT
        if _triggered(lower, ["show projects", "list projects", "all projects", "my projects", "what projects"]):
            return IntentType.SHOW_PROJECTS
        if _triggered(lower, ["project status", "status of project"]):
            return IntentType.SHOW_PROJECT_STATUS
        if _triggered(lower, ["assign member", "add member to project"]):
            return IntentType.ASSIGN_MEMBER
        if _triggered(lower, ["remove member", "remove from project"]):
            return IntentType.REMOVE_MEMBER

        # --- Task intents ---
        if _triggered(lower, ["create task", "new task", "add task", "create a task"]):
            return IntentType.CREATE_TASK
        if _triggered(lower, ["assign task"]):
            return IntentType.ASSIGN_TASK
        if _triggered(lower, ["update task"]):
            return IntentType.UPDATE_TASK
        if _triggered(lower, ["complete task", "mark task", "finish task", "done"]):
            return IntentType.COMPLETE_TASK
        if _triggered(lower, ["delete task", "remove task"]):
            return IntentType.DELETE_TASK
        if _triggered(lower, ["change deadline", "extend deadline", "set deadline", "move deadline", "set a deadline"]):
            return IntentType.CHANGE_DEADLINE
        if _triggered(lower, ["change priority", "set priority", "high priority", "low priority"]):
            return IntentType.CHANGE_PRIORITY
        if _triggered(lower, ["show tasks", "list tasks", "my tasks", "all tasks", "what are my tasks", "show my tasks"]):
            return IntentType.SHOW_TASKS
        if _triggered(lower, ["overdue", "show overdue", "list overdue", "overdue tasks"]):
            return IntentType.SHOW_OVERDUE

        # --- Executive / Daily Briefing intents (high priority, before planner) ---
        if _triggered(lower, [
            "good morning", "good afternoon", "good evening", "start my day",
            "daily briefing", "daily brief", "today's briefing", "morning briefing",
            "today's summary",
            "what should i focus on",
        ]):
            return IntentType.DAILY_BRIEFING

        # --- Planner intents ---
        if _triggered(lower, ["add meeting", "schedule meeting", "book meeting", "set up meeting", "schedule a meeting"]):
            return IntentType.ADD_MEETING
        if _triggered(lower, ["cancel meeting"]):
            return IntentType.CANCEL_MEETING
        if _triggered(lower, ["reschedule meeting", "move meeting"]):
            return IntentType.RESCHEDULE_MEETING
        if _triggered(lower, ["today schedule", "today's schedule", "what today", "my day", "today agenda", "my schedule today", "schedule today"]):
            return IntentType.TODAY_SCHEDULE
        if _triggered(lower, ["week schedule", "this week", "my week", "weekly agenda"]):
            return IntentType.WEEK_SCHEDULE
        if _triggered(lower, ["add reminder", "set reminder", "create reminder", "remind me", "set a reminder"]):
            return IntentType.ADD_REMINDER

        # --- Notification intents ---
        if _triggered(lower, ["create notification", "send notification", "push notification"]):
            return IntentType.CREATE_NOTIFICATION
        if _triggered(lower, ["show notifications", "my notifications", "list notifications", "any notifications"]):
            return IntentType.SHOW_NOTIFICATIONS
        if _triggered(lower, ["mark as read", "mark read", "mark notification"]):
            return IntentType.MARK_AS_READ

        # --- Dashboard intents ---
        if _triggered(lower, ["focus today", "what to focus", "my focus"]):
            return IntentType.FOCUS_TODAY
        if _triggered(lower, ["executive summary", "brief me", "status report", "summary"]):
            return IntentType.EXECUTIVE_SUMMARY
        if _triggered(lower, ["today priorities", "today's priorities", "my priorities", "what's important today"]):
            return IntentType.TODAY_PRIORITIES
        if _triggered(lower, ["business risk", "risks", "what risks", "risk assessment"]):
            return IntentType.BUSINESS_RISK

        return IntentType.GENERAL_CHAT


def _triggered(text: str, phrases: list[str]) -> bool:
    return any(p in text for p in phrases)
