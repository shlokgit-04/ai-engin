from abc import ABC, abstractmethod
from app.document_intelligence.retriever.base import RetrieverResult


class ContextBuilderResult:
    def __init__(self, prompt: str, context_chunks: list[RetrieverResult]) -> None:
        self.prompt = prompt
        self.context_chunks = context_chunks


class BaseContextBuilder(ABC):
    @abstractmethod
    async def build(self, query: str, chunks: list[RetrieverResult]) -> ContextBuilderResult:
        ...
