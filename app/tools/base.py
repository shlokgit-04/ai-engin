from abc import ABC, abstractmethod

from app.orchestrator.context import ExecutionContext
from app.orchestrator.enums import IntentType


class BaseTool(ABC):
    @abstractmethod
    async def execute(self, context: ExecutionContext, intent: IntentType) -> str:
        ...

    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def description(self) -> str:
        ...

    @classmethod
    @abstractmethod
    def supported_actions(cls) -> list[str]:
        ...
