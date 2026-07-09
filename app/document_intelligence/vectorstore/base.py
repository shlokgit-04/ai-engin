from abc import ABC, abstractmethod
from typing import Any
from app.document_intelligence.metadata.classification import DocumentClassification


class VectorSearchResult:
    def __init__(
        self,
        chunk_text: str,
        score: float,
        document_id: str,
        metadata: dict | None = None,
    ) -> None:
        self.chunk_text = chunk_text
        self.score = score
        self.document_id = document_id
        self.metadata = metadata or {}


class BaseVectorStore(ABC):
    @abstractmethod
    async def insert(self, collection: str, vectors: list[list[float]], payloads: list[dict]) -> None:
        ...

    @abstractmethod
    async def delete(self, collection: str, document_id: str) -> None:
        ...

    @abstractmethod
    async def search(
        self,
        collection: str,
        vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        ...

    @abstractmethod
    async def update(self, collection: str, document_id: str, payload: dict) -> None:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
