from abc import ABC, abstractmethod
from typing import AsyncIterator


class ChunkResult:
    def __init__(self, text: str, index: int, metadata: dict | None = None) -> None:
        self.text = text
        self.index = index
        self.metadata = metadata or {}


class BaseChunker(ABC):
    @abstractmethod
    async def chunk(self, text: str) -> list[ChunkResult]:
        ...
