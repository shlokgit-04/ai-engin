import re
import time
from typing import Any, AsyncIterator

from app.orchestrator.enums import RequestCategory, IntentType
from app.orchestrator.classifier import Classifier
from app.orchestrator.context import ExecutionContext
from app.orchestrator.pipeline import ExecutionPipeline
from app.agents.base import BaseAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.meeting_agent import MeetingAgent
from app.agents.task_agent import TaskAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.notification_agent import NotificationAgent
from app.tools.router import ToolRouter
from app.core.logging import logger


_STOP_WORDS = {
    "the", "a", "an", "task", "tasks", "to", "for", "from", "this", "that",
    "member", "members", "project", "projects", "meeting", "meetings",
    "high", "low", "medium", "priority", "tomorrow", "today", "in", "on",
    "at", "with", "team", "user", "please", "my", "new", "create", "add",
    "remove", "assign", "assigned", "read", "mark", "show", "list",
}


class AIOrchestrator:
    def __init__(
        self,
        pipeline: ExecutionPipeline,
        agents: dict[RequestCategory, BaseAgent] | None = None,
        tool_router: ToolRouter | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._classifier = Classifier()
        self._agents = agents if agents is not None else self._build_default_agents()
        self._tool_router = tool_router if tool_router is not None else ToolRouter()

    def _build_default_agents(self) -> dict[RequestCategory, BaseAgent]:
        knowledge = KnowledgeAgent(pipeline=self._pipeline)
        planner = PlannerAgent()
        meeting = MeetingAgent()
        task = TaskAgent()
        finance = FinanceAgent()
        recommendation = RecommendationAgent()
        notification = NotificationAgent()

        return {
            RequestCategory.GENERAL_CHAT: knowledge,
            RequestCategory.COMPANY_KNOWLEDGE: knowledge,
            RequestCategory.DOCUMENT_QUERY: knowledge,
            RequestCategory.DOCUMENT_UPLOAD: planner,
            RequestCategory.IMAGE_ANALYSIS: planner,
            RequestCategory.MEETING: meeting,
            RequestCategory.TASK_ASSISTANT: task,
            RequestCategory.FINANCE: finance,
            RequestCategory.RECOMMENDATION: recommendation,
            RequestCategory.UNKNOWN: knowledge,
        }

    def _select_agent(self, category: RequestCategory) -> BaseAgent:
        agent = self._agents.get(category)
        if agent is not None:
            return agent
        return self._agents.get(RequestCategory.UNKNOWN, list(self._agents.values())[0])

    async def route_request(self, context: ExecutionContext) -> str:
        start = time.monotonic()
        logger.info("Orchestrator processing input", input=context.message[:200])
        category = self._classifier.classify(context.message)
        intent = self._classifier.classify_intent(context.message)
        logger.info("Orchestrator classified", category=category.value, intent=intent.value)
        self._enrich_context(context, intent)
        response = await self._route_request(context, category, intent)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "Orchestrator completed request",
            category=category.value,
            intent=intent.value,
            elapsed_ms=elapsed_ms,
            response_length=len(response),
        )
        return response

    def _extract_person(self, message: str) -> str:
        """Pull a person's name out of a natural-language request."""
        lower = message.lower()
        patterns = [
            r"assign\s+(?:the\s+)?task\b.*?\bto\s+(\S+)",
            r"assign\s+(?:the\s+)?task\s+(?:to\s+)?(\S+)",
            r"assign\s+(\S+)\s+(?:the\s+)?task",
            r"assign\s+to\s+(\S+)",
            r"(?:add|assign|remove|invite)\s+member\s+(\S+)",
            r"(?:add|assign|remove|invite)\s+(\S+)\s+(?:to|from)\s+(?:the\s+)?(?:project|team|task)",
            r"(?:move|transfer)\s+(?:task\s+)?(?:from\s+)?(\S+)\s+to\s+(\S+)",
        ]
        for pat in patterns:
            m = re.search(pat, lower)
            if m:
                for group in m.groups():
                    name = (group or "").strip(".,!?@")
                    if name and name not in _STOP_WORDS and not name.isdigit():
                        return name.capitalize()
        return ""

    def _enrich_context(self, context: ExecutionContext, intent: IntentType) -> None:
        """Populate context metadata that tools rely on (assignee, member)."""
        if context.metadata.get("assignee") or context.metadata.get("member_name"):
            return
        person = self._extract_person(context.message)
        if not person:
            return
        if intent == IntentType.ASSIGN_TASK:
            context.metadata["assignee"] = person
        elif intent in (IntentType.ASSIGN_MEMBER, IntentType.REMOVE_MEMBER):
            context.metadata["member_name"] = person

    async def route_request_stream(self, context: ExecutionContext) -> AsyncIterator[str]:
        category = self._classifier.classify(context.message)
        intent = self._classifier.classify_intent(context.message)
        self._enrich_context(context, intent)

        if intent != IntentType.GENERAL_CHAT:
            response = await self._route_request(context, category, intent)
            for word in response.split(" "):
                yield word + " "
            return

        if category == RequestCategory.GENERAL_CHAT:
            if self._pipeline._provider_llm:
                try:
                    async for chunk in self._pipeline._provider_llm._manager.generate_stream(
                        prompt=context.message,
                    ):
                        yield chunk
                    return
                except Exception as e:
                    logger.warning("Provider stream failed, falling back to non-stream", error=str(e))

        response = await self._route_request(context, category, intent)
        yield response

    async def _route_request(self, context: ExecutionContext, category: RequestCategory, intent: IntentType) -> str:
        start = time.monotonic()

        if intent != IntentType.GENERAL_CHAT:
            tool = self._tool_router.route(intent)
            response = await tool.execute(context, intent)
            handler = tool.name()
        elif category in (RequestCategory.COMPANY_KNOWLEDGE, RequestCategory.DOCUMENT_QUERY):
            agent = self._select_agent(category)
            response = await agent.execute(context, category)
            handler = type(agent).__name__
        else:
            response = await self._pipeline.execute(category, context)
            handler = "ExecutionPipeline"

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "Orchestrator routed request",
            input=context.message[:200],
            category=category.value,
            intent=intent.value,
            handler=handler,
            elapsed_ms=elapsed_ms,
        )
        return response
