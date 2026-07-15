import json as _json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamRequest, ChatAnalyzeRequest
from app.router.chat import ChatRouter
from app.core.dependencies import get_chat_router, get_provider_manager
from app.models.providers.manager import ProviderManager
from app.core.logging import logger

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_router: ChatRouter = Depends(get_chat_router),
) -> ChatResponse:
    return await chat_router.process_message(request)


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    chat_router: ChatRouter = Depends(get_chat_router),
) -> StreamingResponse:
    async def event_generator():
        async for chunk in chat_router.process_message_stream(request):
            payload = _json.dumps({"content": chunk})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/analyze", response_model=ChatResponse)
async def chat_analyze(
    request: ChatAnalyzeRequest,
    manager: ProviderManager = Depends(get_provider_manager),
) -> ChatResponse:
    logger.info(
        "Chat analyze requested",
        message_length=len(request.message),
        temperature=request.temperature,
    )
    response = await manager.generate(
        prompt=request.message,
        system_prompt=request.system_prompt or None,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )
    return ChatResponse(response=response)
