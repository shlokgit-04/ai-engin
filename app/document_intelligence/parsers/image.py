from abc import ABC, abstractmethod


class ImageParser(ABC):
    @abstractmethod
    async def parse(self, file_path: str) -> str:
        ...
