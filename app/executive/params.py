import re
from datetime import datetime, timedelta
from typing import Any

from app.orchestrator.context import ExecutionContext


def extract_project_name(message: str, default: str = "Untitled") -> str:
    parts = message.split()
    for i, w in enumerate(parts):
        if w.lower() in ("project", "projects") and i + 1 < len(parts):
            candidate = parts[i + 1].strip(".,!?")
            if candidate and not candidate.startswith(("status", "report", "named", "called")):
                return candidate
    return default


def extract_project_old_name(message: str) -> str:
    lower = message.lower()
    for prefix in ("rename project", "rename "):
        if prefix in lower:
            start = lower.index(prefix) + len(prefix)
            rest = message[start:].strip()
            if " to " in rest:
                return rest[:rest.lower().index(" to ")].strip()
    return "Project"


def extract_rename_target(message: str) -> str:
    for prefix in ("rename project to", "rename to", "rename project "):
        if prefix in message.lower():
            idx = message.lower().index(prefix) + len(prefix)
            return message[idx:].strip(".,!? ") or "Renamed"
    return "Renamed"


def extract_task_title(message: str, default: str = "Untitled Task") -> str:
    for prefix in ("create task", "new task", "add task", "create a task"):
        if prefix in message.lower():
            idx = message.lower().index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                for word in [
                    " tomorrow", " today", " next week",
                    " high priority", " low priority", " medium priority", " normal priority",
                ]:
                    if candidate.lower().endswith(word):
                        candidate = candidate[:-len(word)].strip()
                return candidate or default
    return default


def extract_task_id(message: str, context: ExecutionContext | None = None) -> str:
    if context and context.project_id:
        return context.project_id
    parts = message.split()
    for i, w in enumerate(parts):
        if w.lower() in ("task", "tasks") and i + 1 < len(parts):
            c = parts[i + 1].strip(".,!?#")
            if c and not c.startswith(("status", "named", "called", "for")):
                return c
    return "default"


def extract_event_title(message: str, default: str = "Event") -> str:
    for prefix in ("schedule", "add", "book", "set up", "create"):
        if prefix in message.lower():
            idx = message.lower().index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            for skip in (" a ", " an ", " meeting ", " event "):
                if candidate.startswith(skip.strip()):
                    candidate = candidate[len(skip.strip()):].strip()
            if candidate:
                return candidate
            return default
    return default


def extract_event_id(message: str, default: str = "default") -> str:
    words = message.split()
    for i, w in enumerate(words):
        if w.lower() in ("meeting", "event") and i + 1 < len(words):
            c = words[i + 1].strip(".,!?")
            if c and not c.startswith(("for", "at", "on", "in", "with")):
                return c
    return default


def extract_date(message: str) -> str | None:
    lower = message.lower()
    if "tomorrow" in lower:
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    if "today" in lower or "now" in lower:
        return datetime.now().strftime("%Y-%m-%d")
    match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})",
        lower,
    )
    if match:
        month_names = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        }
        month = month_names[match.group(1)]
        day = int(match.group(2))
        year = datetime.now().year
        return datetime(year, month, day).strftime("%Y-%m-%d")
    return None


def extract_time(message: str) -> str | None:
    lower = message.lower()
    patterns = [
        r"(\d{1,2}):(\d{2})\s*(am|pm)",
        r"(\d{1,2})\s*(am|pm)",
        r"(\d{1,2}):(\d{2})\b(?!\s*(?:am|pm))",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if not match:
            continue
        groups = match.groups()
        if len(groups) == 3 and groups[2] in ("am", "pm"):
            hour = int(groups[0])
            minute = int(groups[1])
            if groups[2] == "pm" and hour < 12:
                hour += 12
            if groups[2] == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        if len(groups) == 2 and groups[1] in ("am", "pm"):
            hour = int(groups[0])
            if groups[1] == "pm" and hour < 12:
                hour += 12
            if groups[1] == "am" and hour == 12:
                hour = 0
            return f"{hour:02d}:00"
        if len(groups) == 2 and groups[1] not in ("am", "pm"):
            return f"{int(groups[0]):02d}:{int(groups[1]):02d}"
    return None


def extract_priority(message: str) -> str:
    lower = message.lower()
    if "high priority" in lower or " high " in f" {lower} ":
        return "high"
    if "low priority" in lower or " low " in f" {lower} ":
        return "low"
    return "normal"


def extract_project_identifier(message: str) -> str | None:
    lower = message.lower()
    # "delete project id <id>" or "remove project id <id>"
    for prefix in ("delete project id", "remove project id"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    # "delete project <name>" or "remove project <name>"
    for prefix in ("delete project", "remove project"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    # standalone "delete <name>" or "remove <name>"
    words = message.split()
    for i, w in enumerate(words):
        if w.lower() in ("delete", "remove") and i + 1 < len(words):
            c = words[i + 1].strip(".,!?")
            if c and c.lower() not in ("project", "projects", "task", "tasks", "notification", "notifications", "meeting", "meetings", "member", "members"):
                return c
    return None


def extract_task_identifier(message: str) -> str | None:
    lower = message.lower()
    # "delete task id <id>" or "remove task id <id>"
    for prefix in ("delete task id", "remove task id"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    # "delete task <name>" or "remove task <name>"
    for prefix in ("delete task", "remove task"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    # standalone "delete <name>" or "remove <name>" where name isn't a reserved word
    words = message.split()
    for i, w in enumerate(words):
        if w.lower() in ("delete", "remove") and i + 1 < len(words):
            c = words[i + 1].strip(".,!?")
            if c and c.lower() not in ("project", "projects", "task", "tasks", "notification", "notifications", "meeting", "meetings", "member", "members", "all"):
                return c
    return None


def extract_notification_id(message: str) -> str | None:
    lower = message.lower()
    # "mark notification <id> as read" or "mark notification <id>"
    for prefix in ("mark notification", "read notification"):
        if prefix in lower:
            rest = lower[lower.index(prefix) + len(prefix):].strip()
            # strip trailing "as read" or similar
            for suffix in ("as read",):
                if rest.endswith(suffix):
                    rest = rest[:-len(suffix)].strip()
            if rest:
                return rest
    # "notification id <id>"
    if "notification id" in lower:
        idx = lower.index("notification id") + len("notification id")
        candidate = lower[idx:].strip(".,!? ")
        if candidate:
            # take first word
            return candidate.split()[0]
    # standalone id after "notification" word
    words = message.split()
    for i, w in enumerate(words):
        if w.lower() in ("notification", "notifications") and i + 1 < len(words):
            c = words[i + 1].strip(".,!?")
            if c and c.lower() not in ("as", "for", "about", "called", "named", "read"):
                return c
    return None
