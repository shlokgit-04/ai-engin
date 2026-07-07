from abc import ABC, abstractmethod
from typing import Any


class BaseMemory(ABC):
    @abstractmethod
    async def add(self, key: str, value: Any) -> None:
        ...

    @abstractmethod
    async def get(self, key: str) -> Any:
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...
