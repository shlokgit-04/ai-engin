from typing import AsyncIterator

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService
from app.core.logging import logger


class ChatRouter:
    def __init__(self, service: ChatService) -> None:
        self._service = service

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        logger.info("Chat message received", message_length=len(request.message))
        return await self._service.process_message(request.message)

    async def process_message_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        logger.info("Chat stream message received", message_length=len(request.message))
        async for chunk in self._service.process_message_stream(request.message):
            yield chunk
