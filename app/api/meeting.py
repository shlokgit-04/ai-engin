import json

from fastapi import APIRouter, Depends
from app.schemas.meeting import MeetingAnalysisRequest, MeetingAnalysisResponse, MeetingAnalysisData
from app.models.providers.manager import ProviderManager
from app.core.dependencies import get_provider_manager
from app.core.logging import logger

router = APIRouter(tags=["Meeting Intelligence"])

MEETING_ANALYSIS_PROMPT = """You are an expert meeting analyst. Analyze the following meeting transcript and extract structured data.

Return ONLY a valid JSON object with exactly these fields (no markdown, no code fences):
{
  "summary": "A 2-3 sentence executive summary of the meeting",
  "key_points": ["key point 1", "key point 2"],
  "participants": ["participant name 1", "participant name 2"],
  "action_items": [
    {"title": "task title", "description": "detailed description", "priority": "high|medium|low", "suggested_owner": "person name or null", "deadline": "date string or null"}
  ],
  "decisions": ["decision 1"],
  "risks": ["risk 1"],
  "blockers": ["blocker 1"]
}

If a section has no items, use an empty array [].
If a field cannot be determined, use null for strings or [] for arrays.

Meeting Transcript:
"""


@router.post("/meeting/analyze", response_model=MeetingAnalysisResponse)
async def analyze_meeting_transcript(
    request: MeetingAnalysisRequest,
    manager: ProviderManager = Depends(get_provider_manager),
) -> MeetingAnalysisResponse:
    logger.info(
        "Meeting analysis requested",
        meeting_id=request.meeting_id,
        meeting_title=request.meeting_title,
        transcript_length=len(request.transcript),
    )

    prompt = MEETING_ANALYSIS_PROMPT + request.transcript

    try:
        response = await manager.generate(
            prompt=prompt,
            system_prompt="You are a meeting analysis AI. Return ONLY valid JSON. No markdown, no code fences, no explanation.",
            temperature=0.1,
            max_tokens=2048,
        )
    except Exception as e:
        logger.error("Meeting analysis failed", error=str(e))
        fallback_data = MeetingAnalysisData(
            summary=f"Analysis unavailable: AI engine error. The meeting '{request.meeting_title or 'Unknown'}' was submitted for analysis.",
            key_points=["AI analysis service is currently unavailable"],
            participants=[],
            action_items=[],
            decisions=[],
            risks=[],
            blockers=[f"AI analysis engine error: {str(e)[:100]}"],
        )
        return MeetingAnalysisResponse(
            success=True,
            message="Analysis completed with fallback (AI engine unavailable)",
            data=fallback_data,
        )

    parsed = None
    try:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(response[start:end])
    except (json.JSONDecodeError, ValueError):
        pass

    if not parsed:
        parsed = {
            "summary": request.transcript[:500],
            "key_points": [],
            "participants": [],
            "action_items": [],
            "decisions": [],
            "risks": [],
            "blockers": [],
        }

    analysis_data = MeetingAnalysisData(
        summary=parsed.get("summary", ""),
        key_points=parsed.get("key_points", []),
        participants=parsed.get("participants", []),
        action_items=parsed.get("action_items", []),
        decisions=parsed.get("decisions", []),
        risks=parsed.get("risks", []),
        blockers=parsed.get("blockers", []),
    )

    logger.info(
        "Meeting analysis complete",
        meeting_id=request.meeting_id,
        key_points=len(analysis_data.key_points),
        action_items=len(analysis_data.action_items),
    )

    return MeetingAnalysisResponse(
        success=True,
        message="Meeting analysis complete",
        data=analysis_data,
    )
