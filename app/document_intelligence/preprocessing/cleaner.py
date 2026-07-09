from abc import ABC, abstractmethod


class BaseCleaner(ABC):
    @abstractmethod
    async def clean(self, text: str) -> str:
        ...
