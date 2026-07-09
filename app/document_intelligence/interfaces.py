from abc import ABC, abstractmethod
from app.orchestrator.context import ExecutionContext


class BaseDocumentIntelligencePipeline(ABC):
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> str:
        ...
