from abc import ABC, abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...
