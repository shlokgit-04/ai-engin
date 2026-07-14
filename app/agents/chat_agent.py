from typing import AsyncIterator

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
        auth_token = kwargs.get("auth_token")
        context = ExecutionContext(message=input, auth_token=auth_token)
        return await self._orchestrator.route_request(context)

    async def run_stream(
        self,
        input: str,
        auth_token: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        logger.info("ChatAgent processing stream", input_length=len(input))
        context = ExecutionContext(message=input, auth_token=auth_token)
        async for chunk in self._orchestrator.route_request_stream(
            context, provider=provider, model=model
        ):
            yield chunk

    async def execute(self, context: ExecutionContext, category: RequestCategory) -> str:
        return await self._orchestrator.route_request(context)
