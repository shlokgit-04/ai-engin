from abc import ABC, abstractmethod


class EmbeddingResult:
    def __init__(self, text: str, vector: list[float], metadata: dict | None = None) -> None:
        self.text = text
        self.vector = vector
        self.metadata = metadata or {}


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        ...
