import time
from typing import Any

from app.orchestrator.enums import RequestCategory
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
from app.core.logging import logger


class AIOrchestrator:
    def __init__(
        self,
        pipeline: ExecutionPipeline,
        agents: dict[RequestCategory, BaseAgent] | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._classifier = Classifier()
        self._agents = agents if agents is not None else self._build_default_agents()

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
        category = self._classifier.classify(context.message)

        agent = self._select_agent(category)
        response = await agent.execute(context, category)

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "Orchestrator routed request",
            category=category.value,
            agent=type(agent).__name__,
            elapsed_ms=elapsed_ms,
        )
        return response
