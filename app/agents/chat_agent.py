from app.agents.base import BaseAgent
from app.orchestrator.enums import RequestCategory
from app.orchestrator.orchestrator import AIOrchestrator
from app.orchestrator.context import ExecutionContext
from app.core.logging import logger


class ChatAgent(BaseAgent):
    def __init__(self, orchestrator: AIOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def run(self, input: str, **kwargs) -> str:
        logger.info("ChatAgent processing", input_length=len(input))
        context = ExecutionContext(message=input)
        return await self._orchestrator.route_request(context)

    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        return await self._orchestrator.route_request(context)
