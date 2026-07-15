from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class ChatStreamRequest(BaseModel):
    message: str
    provider: str | None = None
    model: str | None = None


class ChatAnalyzeRequest(BaseModel):
    message: str
    temperature: float = 0.1
    max_tokens: int = 2048
    system_prompt: str = ""

