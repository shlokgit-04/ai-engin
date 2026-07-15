from typing import AsyncIterator

from app.schemas.chat import ChatResponse
from app.agents.chat_agent import ChatAgent
from app.memory.base import BaseMemory
from app.core.logging import logger


class ChatService:
    def __init__(self, agent: ChatAgent, memory: BaseMemory | None = None) -> None:
        self._agent = agent
        self._memory = memory

    async def process_message(self, message: str) -> ChatResponse:
        logger.debug("Processing message", message=message)
        response = await self._agent.run(message)
        if self._memory:
            await self._memory.add("default", {"role": "user", "content": message})
            await self._memory.add("default", {"role": "assistant", "content": response})
        return ChatResponse(response=response)

    async def process_message_stream(self, message: str) -> AsyncIterator[str]:
        logger.debug("Processing stream message", message=message)
        async for chunk in self._agent.run_stream(message):
            yield chunk
