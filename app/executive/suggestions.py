_SUGGESTIONS: dict[str, str] = {
    "create_project": "Would you like to create the first task for this project?",
    "delete_project": "Would you like to review your remaining projects?",
    "rename_project": "You can update team members or create tasks next.",
    "create_task": "Would you like to set a deadline or assign this task?",
    "complete_task": "Would you like to review your remaining tasks?",
    "update_task": "You can mark it complete or change the deadline next.",
    "delete_task": "Would you like to create a replacement task?",
    "change_deadline": "Would you like to review all task deadlines?",
    "change_priority": "Would you like to review all task priorities?",
    "assign_task": "The assignee has been notified.",
    "add_meeting": "Would you like me to create reminders for this meeting?",
    "cancel_meeting": "Would you like to reschedule or create a new meeting?",
    "reschedule_meeting": "The updated time has been saved.",
    "add_reminder": "You can set additional reminders if needed.",
    "create_notification": "The notification has been sent.",
    "mark_as_read": "You can view your remaining notifications.",
}


def get_suggestion(intent_value: str) -> str:
    return _SUGGESTIONS.get(intent_value, "")
