import json

from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.core.logging import logger


MEETING_RESPONSE_TEMPLATE = """Meeting Intelligence Summary

**Meeting:** {title}

**Status:** {status}

**Key Information:**
{key_info}

**Analysis Status:** {analysis_status}

For detailed analysis, use the Meeting Intelligence API endpoints:
- POST /meetings/{{id}}/analyze - Run AI analysis on transcript
- GET /meetings/{{id}}/summary - Get executive summary
- GET /meetings/{{id}}/mom - Get structured Minutes of Meeting
"""


class MeetingAgent(BaseAgent):
    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        logger.info("MeetingAgent executing", category=category.value, message=context.message[:100])

        message = context.message.lower()

        if any(phrase in message for phrase in ["analyze meeting", "meeting analysis", "analyze transcript"]):
            return self._format_analysis_guidance()

        if any(phrase in message for phrase in ["meeting summary", "get summary", "show summary"]):
            return self._format_summary_guidance()

        if any(phrase in message for phrase in ["minutes of meeting", "mom", "show mom"]):
            return self._format_mom_guidance()

        if any(phrase in message for phrase in ["upload transcript", "add transcript"]):
            return self._format_transcript_guidance()

        return self._format_general_guidance()

    def _format_analysis_guidance(self) -> str:
        return (
            "To analyze a meeting transcript:\n\n"
            "1. **Upload the transcript** using `POST /meetings/{id}/transcript`\n"
            "2. **Trigger analysis** using `POST /meetings/{id}/analyze`\n\n"
            "The AI will generate:\n"
            "- Executive summary\n"
            "- Key points and decisions\n"
            "- Action items with owners and deadlines\n"
            "- Risks and blockers identification\n\n"
            "Results are stored in the meeting record and can be retrieved via:\n"
            "- `GET /meetings/{id}/summary` - Executive summary\n"
            "- `GET /meetings/{id}/mom` - Structured Minutes of Meeting"
        )

    def _format_summary_guidance(self) -> str:
        return (
            "To get a meeting summary:\n\n"
            "Use `GET /meetings/{id}/summary` to retrieve the AI-generated executive summary.\n\n"
            "If no summary exists, run analysis first:\n"
            "1. `POST /meetings/{id}/analyze`\n"
            "2. Then `GET /meetings/{id}/summary`"
        )

    def _format_mom_guidance(self) -> str:
        return (
            "To get structured Minutes of Meeting:\n\n"
            "Use `GET /meetings/{id}/mom` to retrieve:\n"
            "- Summary\n"
            "- Key points\n"
            "- Participants\n"
            "- Action items\n"
            "- Decisions\n"
            "- Risks and blockers\n\n"
            "If no MoM exists, run analysis first:\n"
            "`POST /meetings/{id}/analyze`"
        )

    def _format_transcript_guidance(self) -> str:
        return (
            "To upload a meeting transcript:\n\n"
            "Use `POST /meetings/{id}/transcript` with:\n"
            "```json\n"
            '{"transcript": "Your meeting transcript text here..."}\n'
            "```\n\n"
            "After uploading, trigger analysis with:\n"
            "`POST /meetings/{id}/analyze`"
        )

    def _format_general_guidance(self) -> str:
        return (
            "Meeting Intelligence is available. You can:\n\n"
            "**Upload & Analyze:**\n"
            "- Upload transcript: `POST /meetings/{id}/transcript`\n"
            "- Run AI analysis: `POST /meetings/{id}/analyze`\n\n"
            "**Retrieve Results:**\n"
            "- Get summary: `GET /meetings/{id}/summary`\n"
            "- Get MoM: `GET /meetings/{id}/mom`\n\n"
            "**Analysis Output:**\n"
            "- Executive summary\n"
            "- Key points and decisions\n"
            "- Action items with owners\n"
            "- Risks and blockers\n\n"
            "What would you like to do with meeting intelligence?"
        )

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return [RequestCategory.MEETING]
