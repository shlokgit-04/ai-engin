from typing import AsyncIterator

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.core.logging import logger


class ChatRouter:
    def __init__(self, service: ChatService) -> None:
        self._service = service

    async def process_message(self, request: ChatRequest, user_auth_token: str | None = None) -> ChatResponse:
        logger.info("Chat message received", message_length=len(request.message))
        return await self._service.process_message(request.message, user_auth_token=user_auth_token)

    async def process_message_stream(self, request: ChatRequest, user_auth_token: str | None = None) -> AsyncIterator[str]:
        logger.info("Chat stream message received", message_length=len(request.message))
        async for chunk in self._service.process_message_stream(request.message, user_auth_token=user_auth_token):
            yield chunk
