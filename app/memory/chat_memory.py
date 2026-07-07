from typing import Any
from app.memory.base import BaseMemory


class ChatMemory(BaseMemory):
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, str]]] = {}

    async def add(self, key: str, value: Any) -> None:
        if key not in self._store:
            self._store[key] = []
        self._store[key].append(value)

    async def get(self, key: str) -> Any:
        return self._store.get(key, [])

    async def clear(self) -> None:
        self._store.clear()
