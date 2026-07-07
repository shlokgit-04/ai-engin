from abc import ABC, abstractmethod


class BaseRAG(ABC):
    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        ...

    @abstractmethod
    async def index(self, documents: list[str]) -> None:
        ...
