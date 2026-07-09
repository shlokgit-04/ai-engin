from typing import Any

from app.memory.base import BaseMemory
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.memory.conversation import ConversationMemory
from app.core.logging import logger


class MemoryManager:
    def __init__(
        self,
        short_term: ShortTermMemory | None = None,
        long_term: LongTermMemory | None = None,
        conversation: ConversationMemory | None = None,
    ) -> None:
        self._short_term = short_term
        self._long_term = long_term
        self._conversation = conversation

    async def remember(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        logger.debug("MemoryManager remember", key=key)
        if self._short_term and ttl_seconds is not None:
            await self._short_term.add(key, value)
            await self._short_term.expire(key, ttl_seconds)
        elif self._long_term:
            await self._long_term.add(key, value)
        else:
            logger.warning("No memory backend available for remember", key=key)

    async def recall(self, key: str) -> Any:
        logger.debug("MemoryManager recall", key=key)
        if self._short_term:
            result = await self._short_term.get(key)
            if result is not None:
                return result
        if self._long_term:
            return await self._long_term.get(key)
        return None

    async def forget(self, key: str) -> None:
        logger.debug("MemoryManager forget", key=key)
        if self._short_term:
            await self._short_term.clear()
        if self._long_term:
            await self._long_term.clear()

    async def summarize(self, key: str) -> str:
        logger.debug("MemoryManager summarize", key=key)
        data = await self.recall(key)
        if not data:
            return ""
        return str(data)
