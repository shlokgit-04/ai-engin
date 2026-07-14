"""Template strings for the ResponseFormatter.

Each template uses Python ``str.format()`` syntax.  The formatter
injects data keys into these templates at runtime.
"""

# ── Projects ──────────────────────────────────────────────────────────────

PROJECT_CREATED = (
    'Project "{name}" has been created successfully.\n\n'
    "Status: {status}\n\n"
    "You can now begin assigning tasks and monitoring progress."
)

PROJECT_DELETED = 'Project "{name}" has been deleted successfully.'

PROJECT_RENAMED = 'Project renamed to "{name}" successfully.'

PROJECT_LIST_HEADER = "You have {count} project(s).\n\n{project_list}"

PROJECT_LIST_ITEM = "  • {name} ({status})"

PROJECT_STATUS = (
    "Project: {name}\n"
    "Status: {status}\n"
    "Progress: {progress}%\n"
    "Deadline: {deadline}\n\n"
    "Current Focus:\n"
    "{focus}"
)

# ── Tasks ─────────────────────────────────────────────────────────────────

TASK_CREATED = (
    "Task created successfully.\n\n"
    "Priority: {priority}\n"
    "Deadline: {due_date}\n\n"
    "Remember to review progress before the deadline."
)

TASK_UPDATED = "Task has been updated successfully."

TASK_ASSIGNED = "Task assigned to {assignee} successfully."

TASK_COMPLETED = "Great. The task has been marked as completed."

TASK_DELETED = 'Task "{name}" has been deleted successfully.'

TASK_DEADLINE_CHANGED = "Deadline changed to {due_date}."

TASK_PRIORITY_CHANGED = "Priority set to {priority}."

TASKS_LIST_HEADER = "You have {count} task(s).\n\n{task_list}"

TASKS_LIST_ITEM = "  • {title} — {status}"

OVERDUE_HEADER = "You have {count} overdue task(s).\n\n{task_list}"

# ── Planner ───────────────────────────────────────────────────────────────

MEETING_SCHEDULED = (
    "Meeting scheduled successfully.\n\n"
    "Date: {date}\n"
    "Time: {time}\n"
    "Reminder Enabled"
)

MEETING_CANCELLED = "Meeting has been cancelled successfully."

MEETING_RESCHEDULED = "Meeting has been rescheduled successfully."

REMINDER_SET = "Reminder set successfully."

TODAY_SCHEDULE = "Today you have {meeting_count} Meetings, {deadline_count} Deadlines, {reminder_count} Reminders."

WEEK_SCHEDULE = "You have {count} event(s) this week.\n\n{event_list}"

EVENTS_LIST_ITEM = "  • {title} at {time}"

# ── Meeting Intelligence ───────────────────────────────────────────────

MEETINGS_LIST_HEADER = "You have {count} meeting(s).\n\n{meeting_list}"

MEETINGS_LIST_ITEM = "  • {title} — {date} at {time}"

MOM_UPLOADED = "Minutes of Meeting uploaded for meeting #{meeting_id} successfully."

MOM_ANALYZED = (
    "Meeting #{meeting_id} MOM Analysis\n\n"
    "Executive Summary:\n{executive_summary}\n\n"
    "Decisions:\n{decisions_list}\n\n"
    "Action Items:\n{action_items_list}\n\n"
    "Risks:\n{risks_list}\n\n"
    "Follow-ups:\n{followups_list}"
)

TASKS_EXTRACTED = (
    "Tasks extracted from meeting #{meeting_id}.\n\n"
    "Meeting Summary Preview:\n{meeting_summary}\n\n"
    "No tasks were automatically created. You can ask me to create specific tasks from this meeting."
)

EXTRACTED_TASKS_LIST_HEADER = "Meeting #{meeting_id} has {count} extracted task(s).\n\n{task_list}"

EXTRACTED_TASKS_ITEM = "  • [{status}] {title} (confidence: {confidence}%)"

EXTRACTED_TASKS_APPROVED = "{count} task(s) approved from meeting #{meeting_id}. Real tasks have been created."

EXTRACTED_TASKS_REJECTED = "{count} task(s) rejected from meeting #{meeting_id}."

MEETING_INVITATION_ACCEPTED = "Meeting invitation accepted successfully."

MEETING_INVITATION_DECLINED = "Meeting invitation declined."

MEETING_ACCEPTED_LIST = "Meeting #{meeting_id} acceptances ({count}):\n\n{names_list}"

MEETING_DECLINED_LIST = "Meeting #{meeting_id} declines ({count}):\n\n{names_list}"

MEETING_TIMELINE_HEADER = "Timeline for meeting #{meeting_id} ({count} event(s)):\n\n{timeline_list}"

MEETING_TIMELINE_ITEM = "  [{action}] {description} ({user})"

MEETING_DECISIONS_HEADER = "Decisions from meeting #{meeting_id}:\n\n{items_list}"

MEETING_RISKS_HEADER = "Risks identified in meeting #{meeting_id}:\n\n{items_list}"

MEETING_FOLLOWUPS_HEADER = "Follow-up items from meeting #{meeting_id}:\n\n{items_list}"

MEETING_BLOCKERS_HEADER = "Blockers from meeting #{meeting_id}:\n\n{items_list}"

LIST_ITEM_BULLET = "  • {item}"

# ── Notifications ─────────────────────────────────────────────────────────

NOTIFICATION_CREATED = "Notification created successfully."

NOTIFICATION_MARKED_READ = "Notification marked as read."

NOTIFICATIONS_HEADER = "You have {count} unread notification(s).\n\n{notification_list}"

NOTIFICATION_ITEM = "• {text}"

# ── Dashboard ─────────────────────────────────────────────────────────────

FOCUS_TODAY = "Focus for today:\n\n{focus}"

EXECUTIVE_SUMMARY = (
    "Good {greeting}.\n\n"
    "Today's Executive Brief\n\n"
    "  • Active Projects: {project_count}\n"
    "  • Pending Tasks: {task_count}\n"
    "  • Overdue Tasks: {overdue_count}\n"
    "  • Meetings Today: {meeting_count}\n"
    "  • Business Risk: {risk_level}\n\n"
    "Highest Priority\n"
    "{top_priority}"
)

TODAY_PRIORITIES = "Today's Priorities\n\n{priority_list}"

PRIORITY_ITEM = "  • {title}"

BUSINESS_RISK = "Risk Assessment\n\n{risk_list}"

RISK_ITEM = "  • [{level}] {description}"

# ── Errors ────────────────────────────────────────────────────────────────

ERROR_NOT_FOUND = "{resource} not found."

ERROR_UNKNOWN = "An unexpected error occurred while processing your request."

ERROR_UNKNOWN_ACTION = "I'm not sure how to handle that request."
