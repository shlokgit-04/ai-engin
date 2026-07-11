"""Executive Summary templates and utilities.

Provides the BRIEFING_TEMPLATE used by ExecutiveBriefingService
and helper functions for constructing summary text.
"""

BRIEFING_TEMPLATE = (
    "Good {greeting}.\n\n"
    "Today's Executive Brief\n\n"
    "  • Tasks: {pending_count} Pending, {overdue_count} Overdue\n"
    "  • Meetings: {meeting_count} Scheduled Today\n"
    "  • Notifications: {unread_notification_count} Unread\n\n"
    "Highest Priority\n"
    "{highest_priority}\n\n"
    "Business Risk\n"
    "{risk_level}\n\n"
    "Insights\n"
    "{insights_text}"
)


def build_briefing_text(
    greeting: str,
    pending_count: int,
    overdue_count: int,
    meeting_count: int,
    unread_notification_count: int,
    highest_priority: str,
    risk_level: str,
    insights_text: str,
) -> str:
    return BRIEFING_TEMPLATE.format(
        greeting=greeting,
        pending_count=pending_count,
        overdue_count=overdue_count,
        meeting_count=meeting_count,
        unread_notification_count=unread_notification_count,
        highest_priority=highest_priority,
        risk_level=risk_level,
        insights_text=insights_text,
    )
