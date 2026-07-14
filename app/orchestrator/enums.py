from enum import Enum


class RequestCategory(Enum):
    GENERAL_CHAT = "GENERAL_CHAT"
    COMPANY_KNOWLEDGE = "COMPANY_KNOWLEDGE"
    DOCUMENT_QUERY = "DOCUMENT_QUERY"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    IMAGE_ANALYSIS = "IMAGE_ANALYSIS"
    MEETING = "MEETING"
    TASK_ASSISTANT = "TASK_ASSISTANT"
    FINANCE = "FINANCE"
    RECOMMENDATION = "RECOMMENDATION"
    UNKNOWN = "UNKNOWN"


class IntentType(str, Enum):
    # Projects
    CREATE_PROJECT = "create_project"
    DELETE_PROJECT = "delete_project"
    RENAME_PROJECT = "rename_project"
    SHOW_PROJECTS = "show_projects"
    SHOW_PROJECT_STATUS = "show_project_status"
    ASSIGN_MEMBER = "assign_member"
    REMOVE_MEMBER = "remove_member"
    # Tasks
    CREATE_TASK = "create_task"
    ASSIGN_TASK = "assign_task"
    UPDATE_TASK = "update_task"
    COMPLETE_TASK = "complete_task"
    DELETE_TASK = "delete_task"
    CHANGE_DEADLINE = "change_deadline"
    CHANGE_PRIORITY = "change_priority"
    SHOW_TASKS = "show_tasks"
    SHOW_OVERDUE = "show_overdue"
    # Planner
    ADD_MEETING = "add_meeting"
    CANCEL_MEETING = "cancel_meeting"
    RESCHEDULE_MEETING = "reschedule_meeting"
    TODAY_SCHEDULE = "today_schedule"
    WEEK_SCHEDULE = "week_schedule"
    ADD_REMINDER = "add_reminder"
    # Meeting Intelligence
    SHOW_MEETINGS = "show_meetings"
    TODAY_MEETINGS = "today_meetings"
    UPCOMING_MEETINGS = "upcoming_meetings"
    SHOW_MEETING_TIMELINE = "show_meeting_timeline"
    UPLOAD_MOM = "upload_mom"
    ANALYZE_MOM = "analyze_mom"
    EXTRACT_TASKS_FROM_MOM = "extract_tasks_from_mom"
    SHOW_EXTRACTED_TASKS = "show_extracted_tasks"
    APPROVE_EXTRACTED_TASKS = "approve_extracted_tasks"
    REJECT_EXTRACTED_TASKS = "reject_extracted_tasks"
    WHO_ACCEPTED = "who_accepted"
    WHO_DECLINED = "who_declined"
    ACCEPT_MEETING = "accept_meeting"
    DECLINE_MEETING = "decline_meeting"
    SHOW_MEETING_DECISIONS = "show_meeting_decisions"
    SHOW_MEETING_RISKS = "show_meeting_risks"
    SHOW_MEETING_FOLLOWUPS = "show_meeting_followups"
    SHOW_MEETING_BLOCKERS = "show_meeting_blockers"
    RENAME_MEETING = "rename_meeting"
    ADD_PARTICIPANT = "add_participant"
    REMOVE_PARTICIPANT = "remove_participant"
    SHOW_MEETING_DETAIL = "show_meeting_detail"
    # Notifications
    CREATE_NOTIFICATION = "create_notification"
    SHOW_NOTIFICATIONS = "show_notifications"
    MARK_AS_READ = "mark_as_read"
    # Dashboard
    FOCUS_TODAY = "focus_today"
    EXECUTIVE_SUMMARY = "executive_summary"
    TODAY_PRIORITIES = "today_priorities"
    BUSINESS_RISK = "business_risk"
    # Executive
    DAILY_BRIEFING = "daily_briefing"
    # General
    GENERAL_CHAT = "general_chat"
