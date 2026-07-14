import re
from datetime import datetime, timedelta
from typing import Any

from app.orchestrator.context import ExecutionContext


def extract_project_name(message: str, default: str = "Untitled") -> str:
    lower = message.lower()
    for trigger in ("create project", "new project", "start project", "build project", "create a project"):
        if trigger in lower:
            idx = lower.index(trigger) + len(trigger)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                for suffix in (" tomorrow", " today", " next week"):
                    if candidate.lower().endswith(suffix):
                        candidate = candidate[:-len(suffix)].strip()
                return candidate or default
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
    lower = message.lower()
    # "rename project X to Y" — extract Y
    if " to " in lower:
        idx = lower.index(" to ") + len(" to ")
        return message[idx:].strip(".,!? ") or "Renamed"
    for prefix in ("rename project to", "rename to"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
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
    lower = message.lower()
    parts = lower.split()
    # First try: look for "task" / "tasks" keyword and take words after it
    for i, w in enumerate(parts):
        if w in ("task", "tasks") and i + 1 < len(parts):
            remaining = parts[i + 1:]
            stop_words = {"to", "on", "for", "by", "from", "done", "completed", "finished"}
            name_words = []
            for rw in remaining:
                cleaned = rw.strip(".,!?#")
                if cleaned in stop_words:
                    break
                name_words.append(rw)
            name = " ".join(name_words).strip(".,!?#")
            if name and name not in ("status", "named"):
                return name
    # Fallback: for intents without "task" keyword (e.g. "Change deadline X to Y")
    # Try to extract a multi-word name from the message after known trigger phrases
    for trigger in ("change deadline", "set deadline", "extend deadline", "move deadline",
                    "change priority", "set priority", "high priority", "low priority"):
        if trigger in lower:
            idx = lower.index(trigger) + len(trigger)
            rest = message[idx:].strip()
            # Strip trailing "to <value>" if present
            if " to " in rest:
                rest = rest[:rest.lower().index(" to ")].strip()
            rest = rest.strip(".,!?#")
            if rest and rest not in ("a", "the", "for"):
                return rest
    return "default"


def extract_event_title(message: str, default: str = "Event") -> str:
    lower = message.lower()
    for prefix in ("create meeting", "new meeting", "add meeting", "schedule meeting", "book meeting", "set up meeting", "schedule a meeting",
                    "schedule", "add", "book", "set up", "create"):
        if lower.startswith(prefix) or f" {prefix}" in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            for skip in (" a ", " an ", " meeting ", " event ", "called ", "named "):
                if candidate.lower().startswith(skip.strip()):
                    candidate = candidate[len(skip.strip()):].strip()
            if candidate:
                time_skip = re.search(r'\b(today|tomorrow|next week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', candidate, re.IGNORECASE)
                if time_skip:
                    candidate = candidate[:time_skip.start()].strip(".,!? ")
                time_match = re.search(r'\b\d{1,2}(:\d{2})?\s*(am|pm)\b', candidate, re.IGNORECASE)
                if time_match:
                    candidate = candidate[:time_match.start()].strip(".,!? ")
                date_match = re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b', candidate, re.IGNORECASE)
                if date_match:
                    candidate = candidate[:date_match.start()].strip(".,!? ")
                return candidate if candidate else default
            return default
    return default


def extract_event_id(message: str, default: str = "default") -> str:
    lower = message.lower()
    stop_words = {"for", "at", "on", "in", "with", "to", "from", "tomorrow", "today",
                  "next", "monday", "tuesday", "wednesday", "thursday", "friday",
                  "saturday", "sunday", "am", "pm",
                  "decisions:", "risks:", "follow-ups:", "followups:", "blockers:",
                  "action", "tasks:", "executive", "summary:", "participants:",
                  "decisions", "risks", "follow-ups", "followups", "blockers"}
    date_words = {"january", "february", "march", "april", "may", "june",
                  "july", "august", "september", "october", "november", "december"}

    for prefix in ("delete meeting", "remove meeting", "cancel meeting",
                    "reschedule meeting", "move meeting", "rename meeting",
                    "upload mom for meeting", "upload minutes for meeting",
                    "analyze meeting", "extract tasks from meeting",
                    "accept meeting", "decline meeting",
                    "show meeting", "meeting details",
                    "show participants for meeting", "meeting participants for"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            rest = message[idx:].strip(".,!? ")
            if rest:
                words = rest.split()
                name_words = []
                for w in words:
                    wl = w.lower().strip(".,!?")
                    if wl in stop_words or wl in date_words:
                        break
                    if re.match(r'^\d{1,2}(:\d{2})?\s*(am|pm)$', wl):
                        break
                    name_words.append(w.strip(".,!?"))
                if name_words:
                    return " ".join(name_words)

    for to_from_marker in (" to ", " from "):
        if to_from_marker in lower:
            idx = lower.rindex(to_from_marker) + len(to_from_marker)
            rest = message[idx:].strip(".,!? ")
            if rest:
                words = rest.split()
                name_words = []
                for w in words:
                    wl = w.lower().strip(".,!?")
                    if wl in stop_words or wl in date_words:
                        break
                    if re.match(r'^\d{1,2}(:\d{2})?\s*(am|pm)$', wl):
                        break
                    name_words.append(w.strip(".,!?"))
                if name_words:
                    candidate = " ".join(name_words)
                    reserved = {"meeting", "event", "the", "a", "an", "user", "participant", "member"}
                    if candidate.lower() not in reserved:
                        return candidate

    for marker in ("meeting", "event"):
        words = message.split()
        for i, w in enumerate(words):
            if w.lower() == marker and i + 1 < len(words):
                name_words = []
                for j in range(i + 1, len(words)):
                    wl = words[j].lower().strip(".,!?")
                    if wl in stop_words or wl in date_words:
                        break
                    if re.match(r'^\d{1,2}(:\d{2})?\s*(am|pm)$', wl):
                        break
                    name_words.append(words[j].strip(".,!?"))
                if name_words:
                    return " ".join(name_words)
    return default


def extract_meeting_name(message: str) -> str | None:
    return extract_event_id(message, default=None) if extract_event_id(message) != "default" else None


def extract_participant_name(message: str) -> str | None:
    lower = message.lower()
    for prefix in ("add participant", "add member", "invite", "add"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            rest = message[idx:].strip(".,!? ")
            if rest:
                words = rest.split()
                name_words = []
                for w in words:
                    wl = w.lower().strip(".,!?")
                    if wl in ("to", "from", "meeting", "event"):
                        break
                    name_words.append(w.strip(".,!?"))
                if name_words:
                    return " ".join(name_words)
    for prefix in ("remove participant", "remove member", "remove"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            rest = message[idx:].strip(".,!? ")
            if rest:
                words = rest.split()
                name_words = []
                for w in words:
                    wl = w.lower().strip(".,!?")
                    if wl in ("to", "from", "meeting", "event"):
                        break
                    name_words.append(w.strip(".,!?"))
                if name_words:
                    return " ".join(name_words)
    return None


def extract_new_meeting_name(message: str) -> str | None:
    lower = message.lower()
    if " to " in lower:
        idx = lower.index(" to ") + len(" to ")
        rest = message[idx:].strip(".,!? ")
        if rest:
            words = rest.split()
            name_words = []
            for w in words:
                wl = w.lower().strip(".,!?")
                if wl in ("for", "at", "on", "in", "tomorrow", "today"):
                    break
                name_words.append(w.strip(".,!?"))
            if name_words:
                return " ".join(name_words)
    return None


def extract_assignee(message: str) -> str:
    """Extract the assignee name from 'Assign task X to Y' pattern."""
    lower = message.lower()
    if " to " in lower:
        idx = lower.rindex(" to ") + len(" to ")
        return message[idx:].strip(".,!? ") or "user"
    return "user"


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
    # "rename project <old> to <new>" — extract old name
    if "rename project" in lower:
        idx = lower.index("rename project") + len("rename project")
        rest = message[idx:].strip()
        if " to " in rest:
            return rest[:rest.lower().index(" to ")].strip()
        return rest.strip(".,!? ") or None
    # "delete project id <id>" or "remove project id <id>"
    for prefix in ("delete project id", "remove project id"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    # "delete project <name>" / "remove project <name>" / "show project <name>"
    for prefix in ("delete project", "remove project", "show project"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    # "project status <name>" / "status of project <name>"
    for prefix in ("project status", "status of project"):
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
    # "mark all notifications as read" / "mark all as read"
    if "mark all" in lower and "read" in lower:
        return "all"
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


def extract_notification_title(message: str, default: str = "Notification") -> str:
    lower = message.lower()
    for prefix in ("create notification", "send notification", "push notification"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    return default


def extract_notification_type(message: str) -> str:
    lower = message.lower()
    if any(w in lower for w in ("deadline", "due", "overdue")):
        return "deadline"
    if any(w in lower for w in ("meeting", "call", "conference")):
        return "meeting_reminder"
    if any(w in lower for w in ("task", "assign", "todo")):
        return "task_assigned"
    if any(w in lower for w in ("project", "update", "milestone")):
        return "project_update"
    return "finance_reminder"


def extract_mom_text(message: str) -> str:
    """Extract the minutes of meeting text from user message."""
    lower = message.lower()
    for prefix in ("upload mom for meeting", "upload minutes for meeting",
                    "upload mom for", "upload minutes for",
                    "upload mom", "upload minutes", "upload meeting notes",
                    "save mom", "save minutes"):
        if prefix in lower:
            idx = lower.index(prefix) + len(prefix)
            rest = message[idx:].strip(".,!? ")
            if rest:
                stop_words = {"for", "at", "on", "in", "with", "to", "from",
                              "tomorrow", "today", "next", "monday", "tuesday",
                              "wednesday", "thursday", "friday", "saturday", "sunday",
                              "decisions:", "risks:", "follow-ups:", "followups:", "blockers:",
                              "action", "tasks:", "executive", "summary:", "participants:",
                              "decisions", "risks", "follow-ups", "followups", "blockers"}
                words = rest.split()
                name_words = []
                skip_count = 0
                for w in words:
                    wl = w.lower().strip(".,!?")
                    if wl in stop_words:
                        break
                    if re.match(r'^\d{1,2}(:\d{2})?\s*(am|pm)$', wl):
                        break
                    name_words.append(w)
                    skip_count += 1
                if name_words:
                    remaining_start = len(" ".join(words[:skip_count]))
                    mom_text = rest[remaining_start:].strip(" -:,.")
                    if mom_text:
                        return mom_text
                return rest
    return message.strip()


def extract_meeting_for_mom(message: str) -> str | None:
    """Extract meeting name/id from 'extract tasks from meeting X' pattern."""
    lower = message.lower()
    for pattern in ("from meeting", "from mom", "from minutes", "for meeting"):
        if pattern in lower:
            idx = lower.index(pattern) + len(pattern)
            candidate = message[idx:].strip(".,!? ")
            if candidate:
                return candidate
    return None
