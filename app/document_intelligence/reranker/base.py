from abc import ABC, abstractmethod
from typing import Any

from app.document_intelligence.retriever.base import RetrieverResult


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[RetrieverResult],
        top_k: int | None = None,
    ) -> list[RetrieverResult]:
        ...

    @abstractmethod
    async def score(
        self,
        query: str,
        document: str,
    ) -> float:
        ...
