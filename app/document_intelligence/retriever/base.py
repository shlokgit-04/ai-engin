from abc import ABC, abstractmethod
from typing import Any


class RetrieverResult:
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


class BaseRetriever(ABC):
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 10) -> list[RetrieverResult]:
        ...

    @abstractmethod
    async def retrieve_by_project(
        self, query: str, project_id: str, top_k: int = 10
    ) -> list[RetrieverResult]:
        ...

    @abstractmethod
    async def retrieve_by_department(
        self, query: str, department: str, top_k: int = 10
    ) -> list[RetrieverResult]:
        ...

    @abstractmethod
    async def retrieve_by_document(
        self, query: str, document_id: str, top_k: int = 10
    ) -> list[RetrieverResult]:
        ...

    @abstractmethod
    async def retrieve_by_metadata(
        self, query: str, filters: dict[str, Any], top_k: int = 10
    ) -> list[RetrieverResult]:
        ...
