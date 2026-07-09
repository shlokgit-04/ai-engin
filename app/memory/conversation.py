from abc import abstractmethod
from typing import Any

from app.memory.base import BaseMemory


class ConversationMemory(BaseMemory):
    @abstractmethod
    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        ...

    @abstractmethod
    async def add_message(self, session_id: str, role: str, content: str) -> None:
        ...

    @abstractmethod
    async def clear_session(self, session_id: str) -> None:
        ...
