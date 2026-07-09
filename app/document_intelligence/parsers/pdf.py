from abc import ABC, abstractmethod


class PDFParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> str:
        ...
