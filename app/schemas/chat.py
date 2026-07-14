from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    auth_token: Optional[str] = None


class ChatStreamRequest(BaseModel):
    message: str
    auth_token: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
