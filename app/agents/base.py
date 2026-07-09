from abc import ABC, abstractmethod
from typing import Any

from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext


class BaseAgent(ABC):
    async def run(self, input: str, **kwargs: Any) -> str:
        context = kwargs.get("context") or ExecutionContext(message=input)
        category = kwargs.get("category") or RequestCategory.GENERAL_CHAT
        return await self.execute(context, category)

    @abstractmethod
    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        ...

    async def health_check(self) -> bool:
        return True

    @classmethod
    def supported_categories(cls) -> list[RequestCategory]:
        return []
