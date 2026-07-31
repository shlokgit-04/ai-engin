import json as _json

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamRequest, ChatAnalyzeRequest
from app.router.chat import ChatRouter
from app.core.dependencies import get_chat_router, get_provider_manager
from app.models.providers.manager import ProviderManager
from app.core.logging import logger

router = APIRouter(tags=["Chat"])


def _extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return token or None
    return None


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
    chat_router: ChatRouter = Depends(get_chat_router),
) -> ChatResponse:
    return await chat_router.process_message(request, user_auth_token=_extract_bearer(authorization))


@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    authorization: str | None = Header(default=None),
    chat_router: ChatRouter = Depends(get_chat_router),
) -> StreamingResponse:
    async def event_generator():
        async for chunk in chat_router.process_message_stream(
            request, user_auth_token=_extract_bearer(authorization)
        ):
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
