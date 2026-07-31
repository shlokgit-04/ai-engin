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


def extract_task_update_title(message: str, default: str = "Untitled Task") -> str:
    for prefix in ("update task", "rename task"):
        if prefix in message.lower():
            idx = message.lower().index(prefix) + len(prefix)
            rest = message[idx:].strip(".,!? ")
            if " to " in rest.lower():
                rest = rest[rest.lower().index(" to ") + 4:].strip()
            return rest or default
    return default


def _clean_task_title(candidate: str) -> str:
    candidate = candidate.strip(".,!?:; ")
    lowered = candidate.lower()
    # strip trailing "due <date>" / ", due ..." / "by <date>"
    m = re.search(r",?\s*(?:due|by)\s+(?:(?:on|the)\s+)?[^,.;!?]+$", lowered)
    if m:
        candidate = candidate[: m.start()].strip(".,!?:; ")
        lowered = candidate.lower()
    for suffix in (" high priority", " medium priority", " low priority", " normal priority", " critical priority", " next week", " tomorrow", " today"):
        if lowered.rstrip(" .").endswith(suffix):
            candidate = candidate[: -len(suffix)].strip(".,!?:; ")
            lowered = candidate.lower()
    # strip leading assignment phrases and connectors
    candidate = re.sub(
        r"^(?:assigned to me\s*[:,-]?\s*|assign(?:ed)? me\s*[:,-]?\s*|assigned to\s+[^,:]{0,40}?[:,-]?\s*|for me\s*[:,-]?\s*|to me\s*[:,-]?\s*|to\s+|assigned\s*[:,-]?\s*)[,:]?\s*",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"^to\s+", "", candidate, flags=re.IGNORECASE).strip(".,!?:; ")
    return candidate


def extract_task_title(message: str, default: str = "Untitled Task") -> str:
    for prefix in ("create a task", "create task", "new task", "add a task", "add task"):
        if prefix in message.lower():
            idx = message.lower().index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return _clean_task_title(candidate) or default
    return default


def extract_task_id(message: str, context: ExecutionContext | None = None) -> str:
    if context and context.project_id:
        return context.project_id
    parts = message.split()
    for i, w in enumerate(parts):
        if w.lower() in ("task", "tasks") and i + 1 < len(parts):
            c = parts[i + 1].strip(".,!?#")
            if c and not c.startswith(("status", "named", "called", "for", "to", "from", "the", "a", "an", "in", "on", "at", "with", "by")):
                return c
    return "default"


_TITLE_STOP_WORDS = {
    "a", "an", "the", "my", "me", "for", "to", "about", "of", "on", "at",
    "with", "in", "by", "this", "next", "please", "kindly", "us", "our",
}
_TITLE_WEEKDAYS = {
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
}
_TITLE_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
}


def _is_title_noise_word(word: str) -> bool:
    wl = word.lower().strip(".,!?:;")
    if not wl:
        return True
    if wl in _TITLE_STOP_WORDS:
        return True
    if wl in _TITLE_WEEKDAYS or wl in _TITLE_MONTHS:
        return True
    if wl in ("meeting", "event", "reminder", "tomorrow", "today"):
        return True
    if re.match(r"^\d{1,2}(:\d{2})?\s*(am|pm)?$", wl):
        return True
    if re.match(r"^\d{4}-\d{2}-\d{2}$", wl) or re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", wl):
        return True
    return False


def _trim_event_title(raw: str) -> str:
    words = raw.split()
    cleaned = []
    for w in words:
        if _is_title_noise_word(w):
            if cleaned:
                break
            continue
        cleaned.append(w)
    return " ".join(cleaned).strip(".,!?:; ")


def extract_event_title(message: str, default: str = "Event") -> str:
    lower = message.lower()
    # 1. Explicit "titled/called/named <title>" — take everything after the marker
    for marker in ("titled", "called", "named"):
        m = re.search(rf"\b{marker}\s+(.+)$", message, re.IGNORECASE)
        if m:
            return _trim_event_title(m.group(1)) or default
    # 2. Strip the leading scheduling verb (longest prefixes first)
    for prefix in (
        "schedule a meeting", "schedule an event", "schedule a reminder",
        "set up a meeting", "set up an event", "set up a reminder", "set up",
        "set a reminder", "set a meeting", "set an event", "set a",
        "book a meeting", "book an event", "book a", "book",
        "add a meeting", "add an event", "add a reminder", "add a", "add",
        "create a meeting", "create an event", "create a reminder", "create a",
        "plan a meeting", "plan an event", "plan",
        "remind me to", "remind me about", "remind me of", "remind me",
        "schedule", "create", "remind",
    ):
        idx = lower.find(prefix)
        if idx != -1:
            candidate = message[idx + len(prefix):].strip(".,:!? ")
            title = _trim_event_title(candidate)
            if title:
                return title
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
    # ISO YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", message)
    if match:
        try:
            year, month, day = (int(g) for g in match.groups())
            return datetime(year, month, day).strftime("%Y-%m-%d")
        except ValueError:
            pass
    # "due this friday" / "next monday" / "coming friday"
    weekday_names = [
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    ]
    match = re.search(
        r"\b(?:this|next|coming)?\s*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        lower,
    )
    if match:
        today = datetime.now()
        target = weekday_names.index(match.group(1))
        delta = (target - today.weekday()) % 7
        if delta == 0:
            delta = 7
        return (today + timedelta(days=delta)).strftime("%Y-%m-%d")
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
    if "high priority" in lower or " high " in f" {lower} " or "critical priority" in lower:
        return "high"
    if "critical" in lower:
        return "critical"
    if "low priority" in lower or " low " in f" {lower} ":
        return "low"
    return "medium"


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
