from abc import ABC, abstractmethod
from typing import Any

from app.memory.base import BaseMemory


class ShortTermMemory(BaseMemory, ABC):
    @abstractmethod
    async def expire(self, key: str, ttl_seconds: int) -> None:
        ...
