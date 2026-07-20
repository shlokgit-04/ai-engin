from pydantic import BaseModel
from typing import Optional, List


class MeetingAnalysisRequest(BaseModel):
    transcript: str
    meeting_id: Optional[int] = None
    meeting_title: Optional[str] = None


class ActionItem(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    suggested_owner: Optional[str] = None
    deadline: Optional[str] = None


class MeetingAnalysisData(BaseModel):
    summary: str = ""
    key_points: List[str] = []
    participants: List[str] = []
    action_items: List[ActionItem] = []
    decisions: List[str] = []
    risks: List[str] = []
    blockers: List[str] = []


class MeetingAnalysisResponse(BaseModel):
    success: bool = True
    message: str = ""
    data: Optional[MeetingAnalysisData] = None
