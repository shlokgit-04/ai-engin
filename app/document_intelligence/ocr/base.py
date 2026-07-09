from abc import ABC, abstractmethod


class BaseOCR(ABC):
    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        ...

    @abstractmethod
    async def is_scanned(self, file_path: str) -> bool:
        ...
