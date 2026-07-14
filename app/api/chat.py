from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamRequest
from app.router.chat import ChatRouter
from app.core.dependencies import get_chat_router, get_execution_pipeline

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_router: ChatRouter = Depends(get_chat_router),
) -> ChatResponse:
    return await chat_router.process_message(request.message, auth_token=request.auth_token)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    chat_router: ChatRouter = Depends(get_chat_router),
) -> StreamingResponse:
    return await chat_router.process_message_stream(
        request.message,
        auth_token=request.auth_token,
        provider=request.provider,
        model=request.model,
    )


class AnalyzeRequest(BaseModel):
    message: str
    system_prompt: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 2048


@router.post("/chat/analyze", response_model=ChatResponse)
async def chat_analyze(
    request: AnalyzeRequest,
):
    pipeline = get_execution_pipeline()
    response = await pipeline.generate(
        prompt=request.message,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    return ChatResponse(response=response)
