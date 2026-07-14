import json
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatResponse
from app.services.chat import ChatService
from app.core.logging import logger


class ChatRouter:
    def __init__(self, service: ChatService) -> None:
        self._service = service

    async def process_message(self, message: str, auth_token: str | None = None) -> ChatResponse:
        logger.info("Chat message received", message_length=len(message))
        return await self._service.process_message(message, auth_token=auth_token)

    async def process_message_stream(
        self,
        message: str,
        auth_token: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> StreamingResponse:
        logger.info("Chat stream requested", message_length=len(message), provider=provider, model=model)

        async def event_generator():
            try:
                async for chunk in self._service.process_message_stream(
                    message,
                    auth_token=auth_token,
                    provider=provider,
                    model=model,
                ):
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
            except Exception as e:
                logger.error("Stream error", error=str(e))
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
