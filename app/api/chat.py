from fastapi import APIRouter, Depends
from app.schemas.chat import ChatRequest, ChatResponse
from app.router.chat import ChatRouter
from app.core.dependencies import get_chat_router

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_router: ChatRouter = Depends(get_chat_router),
) -> ChatResponse:
    return await chat_router.process_message(request)
