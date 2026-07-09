from abc import abstractmethod
from typing import Any

from app.memory.base import BaseMemory


class LongTermMemory(BaseMemory):
    @abstractmethod
    async def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        ...
