from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


class ExecutionContext(BaseModel):
    message: str
    user_id: str | None = None
    username: str | None = None
    role: str | None = None
    department: str | None = None
    project_id: str | None = None
    session_id: str | None = None
    conversation_history: list[dict[str, str]] | None = None
    uploaded_files: list[str] | None = None
    attachments: list[str] | None = None
    request_timestamp: datetime | None = None
    request_source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
