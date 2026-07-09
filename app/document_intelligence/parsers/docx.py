from abc import ABC, abstractmethod


class DocxParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> str:
        ...
