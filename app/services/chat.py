from typing import AsyncIterator

from app.schemas.chat import ChatResponse
from app.agents.chat_agent import ChatAgent
from app.memory.base import BaseMemory
from app.core.logging import logger


class ChatService:
    def __init__(self, agent: ChatAgent, memory: BaseMemory | None = None) -> None:
        self._agent = agent
        self._memory = memory

    async def process_message(self, message: str, auth_token: str | None = None) -> ChatResponse:
        logger.debug("Processing message", message=message)
        response = await self._agent.run(message, auth_token=auth_token)
        if self._memory:
            await self._memory.add("default", {"role": "user", "content": message})
            await self._memory.add("default", {"role": "assistant", "content": response})
        return ChatResponse(response=response)

    async def process_message_stream(
        self,
        message: str,
        auth_token: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        logger.debug("Processing stream message", message=message, provider=provider)
        async for chunk in self._agent.run_stream(
            message, auth_token=auth_token, provider=provider, model=model
        ):
            yield chunk
