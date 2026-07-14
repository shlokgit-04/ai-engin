"""Architecture integrity tests.

Verifies the enterprise multi-agent architecture is correctly wired:
  - All agents inherit BaseAgent and implement required methods.
  - Category-to-agent mapping covers every RequestCategory.
  - Orchestrator selects KnowledgeAgent for chat/knowledge categories.
  - Memory, security, and reranker interfaces are defined.
  - Dependency injection returns correct types.
  - Zero regression: existing behaviour is unchanged.
"""

import pytest
from typing import Any

from app.orchestrator.enums import RequestCategory
from app.orchestrator.context import ExecutionContext
from app.orchestrator.orchestrator import AIOrchestrator
from app.orchestrator.pipeline import ExecutionPipeline, FEATURE_PLACEHOLDER
from app.agents.base import BaseAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.meeting_agent import MeetingAgent
from app.agents.task_agent import TaskAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.memory.manager import MemoryManager
from app.memory.short_term import ShortTermMemory
from app.memory.long_term import LongTermMemory
from app.memory.conversation import ConversationMemory
from app.document_intelligence.reranker.base import BaseReranker
from app.security.permission_guard import PermissionGuard
from app.document_intelligence.metadata.models import DocumentMetadata
from app.models.base import BaseLLM
from app.models.providers.base import ProviderHealth
from app.models.providers.manager import ProviderManager
from app.core.dependencies import (
    get_knowledge_agent,
    get_planner_agent,
    get_finance_agent,
    get_meeting_agent,
    get_task_agent,
    get_notification_agent,
    get_recommendation_agent,
    get_agent_map,
    get_memory_manager,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeLLM(BaseLLM):
    async def generate_response(self, prompt: str, **kwargs: Any) -> str:
        return f"fake:{prompt}"

    async def health_check(self) -> bool:
        return True


class FakeKnowledgePipe:
    async def execute(self, context: ExecutionContext) -> str:
        return "Document Intelligence Pipeline not implemented yet."


class _FakeProvider:
    """Minimal AIProvider stand-in for tests."""
    provider_name = "fake"
    current_model = "fake-model"

    async def generate(self, prompt, **kwargs):
        return f"fake:{prompt}"

    async def generate_stream(self, prompt, **kwargs):
        yield f"fake:{prompt}"

    async def health_check(self):
        return ProviderHealth(healthy=True, provider="fake", message="ok")

    def list_models(self):
        return []


@pytest.fixture
def pipeline() -> ExecutionPipeline:
    pm = ProviderManager(providers={"fake": _FakeProvider()}, default_provider="fake")
    return ExecutionPipeline(
        provider_manager=pm,
        gemini=FakeLLM(),
        ollama=FakeLLM(),
        knowledge_pipeline=FakeKnowledgePipe(),
    )


@pytest.fixture
def orchestrator(pipeline: ExecutionPipeline) -> AIOrchestrator:
    return AIOrchestrator(pipeline=pipeline)


# ---------------------------------------------------------------------------
# 1.  Agent base-class compliance
# ---------------------------------------------------------------------------

AGENT_CLASSES = [
    KnowledgeAgent,
    PlannerAgent,
    FinanceAgent,
    MeetingAgent,
    TaskAgent,
    NotificationAgent,
    RecommendationAgent,
]


class TestAgentContract:
    """Every specialised agent must honour the BaseAgent contract."""

    @pytest.mark.parametrize("cls", AGENT_CLASSES)
    def test_inherits_base_agent(self, cls: type) -> None:
        assert issubclass(cls, BaseAgent), f"{cls.__name__} does not inherit BaseAgent"

    @pytest.mark.parametrize("cls", AGENT_CLASSES)
    def test_has_execute_method(self, cls: type) -> None:
        assert hasattr(cls, "execute"), f"{cls.__name__} missing execute()"

    @pytest.mark.parametrize("cls", AGENT_CLASSES)
    def test_has_health_check_method(self, cls: type) -> None:
        assert hasattr(cls, "health_check"), f"{cls.__name__} missing health_check()"

    @pytest.mark.parametrize("cls", AGENT_CLASSES)
    def test_has_supported_categories_method(self, cls: type) -> None:
        assert hasattr(cls, "supported_categories"), f"{cls.__name__} missing supported_categories()"

    @pytest.mark.parametrize("cls", AGENT_CLASSES)
    def test_supported_categories_returns_list(self, cls: type) -> None:
        cats = cls.supported_categories()
        assert isinstance(cats, list), f"{cls.__name__}.supported_categories() should return list"
        for c in cats:
            assert isinstance(c, RequestCategory), f"{cls.__name__} has non-RequestCategory entry {c}"

    @pytest.mark.parametrize("cls", AGENT_CLASSES)
    def test_can_instantiate(self, cls: type, pipeline: ExecutionPipeline) -> None:
        if cls is KnowledgeAgent:
            instance = cls(pipeline=pipeline)  # type: ignore[call-arg]
        else:
            instance = cls()  # type: ignore[call-arg]
        assert isinstance(instance, cls)


# ---------------------------------------------------------------------------
# 2.  Orchestrator agent selection
# ---------------------------------------------------------------------------

class TestOrchestratorAgentSelection:
    """The orchestrator must dispatch the correct agent per category."""

    def test_selects_knowledge_agent_for_general_chat(
        self, orchestrator: AIOrchestrator
    ) -> None:
        agent = orchestrator._select_agent(RequestCategory.GENERAL_CHAT)
        assert isinstance(agent, KnowledgeAgent), "GENERAL_CHAT should map to KnowledgeAgent"

    def test_selects_knowledge_agent_for_company_knowledge(
        self, orchestrator: AIOrchestrator
    ) -> None:
        agent = orchestrator._select_agent(RequestCategory.COMPANY_KNOWLEDGE)
        assert isinstance(agent, KnowledgeAgent), "COMPANY_KNOWLEDGE should map to KnowledgeAgent"

    def test_selects_planner_for_document_upload(
        self, orchestrator: AIOrchestrator
    ) -> None:
        agent = orchestrator._select_agent(RequestCategory.DOCUMENT_UPLOAD)
        assert isinstance(agent, PlannerAgent), "DOCUMENT_UPLOAD should map to PlannerAgent"

    def test_selects_meeting_agent(self, orchestrator: AIOrchestrator) -> None:
        agent = orchestrator._select_agent(RequestCategory.MEETING)
        assert isinstance(agent, MeetingAgent), "MEETING should map to MeetingAgent"

    def test_selects_task_agent(self, orchestrator: AIOrchestrator) -> None:
        agent = orchestrator._select_agent(RequestCategory.TASK_ASSISTANT)
        assert isinstance(agent, TaskAgent), "TASK_ASSISTANT should map to TaskAgent"

    def test_selects_finance_agent(self, orchestrator: AIOrchestrator) -> None:
        agent = orchestrator._select_agent(RequestCategory.FINANCE)
        assert isinstance(agent, FinanceAgent), "FINANCE should map to FinanceAgent"

    def test_selects_recommendation_agent(self, orchestrator: AIOrchestrator) -> None:
        agent = orchestrator._select_agent(RequestCategory.RECOMMENDATION)
        assert isinstance(agent, RecommendationAgent), "RECOMMENDATION should map to RecommendationAgent"

    def test_selects_knowledge_agent_for_unknown(
        self, orchestrator: AIOrchestrator
    ) -> None:
        agent = orchestrator._select_agent(RequestCategory.UNKNOWN)
        assert isinstance(agent, KnowledgeAgent), "UNKNOWN should fall back to KnowledgeAgent"


# ---------------------------------------------------------------------------
# 3.  Agent behaviour
# ---------------------------------------------------------------------------

class TestKnowledgeAgentBehaviour:
    """KnowledgeAgent is the only agent that executes today."""

    @pytest.mark.asyncio
    async def test_execute_delegates_to_pipeline(
        self, pipeline: ExecutionPipeline
    ) -> None:
        agent = KnowledgeAgent(pipeline=pipeline)
        ctx = ExecutionContext(message="test")
        result = await agent.execute(ctx, RequestCategory.GENERAL_CHAT)
        assert result == "fake:test"


class TestPlaceholderAgentBehaviour:
    """All other agents return FEATURE_PLACEHOLDER."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cls",
        [PlannerAgent, FinanceAgent, MeetingAgent, TaskAgent,
         NotificationAgent, RecommendationAgent],
    )
    async def test_execute_returns_placeholder(self, cls: type) -> None:
        instance = cls()
        result = await instance.execute(
            ExecutionContext(message="anything"), RequestCategory.GENERAL_CHAT
        )
        assert result == FEATURE_PLACEHOLDER, (
            f"{cls.__name__} should return FEATURE_PLACEHOLDER"
        )


# ---------------------------------------------------------------------------
# 4.  Memory interfaces
# ---------------------------------------------------------------------------

class TestMemoryInterfaces:
    """Memory components must be instantiatable or importable."""

    def test_memory_manager_constructs(self) -> None:
        mgr = MemoryManager()
        assert mgr is not None
        assert callable(mgr.remember)
        assert callable(mgr.recall)
        assert callable(mgr.forget)
        assert callable(mgr.summarize)

    def test_short_term_memory_interface(self) -> None:
        assert hasattr(ShortTermMemory, "add")
        assert hasattr(ShortTermMemory, "get")
        assert hasattr(ShortTermMemory, "clear")
        assert hasattr(ShortTermMemory, "expire")

    def test_long_term_memory_interface(self) -> None:
        assert hasattr(LongTermMemory, "add")
        assert hasattr(LongTermMemory, "get")
        assert hasattr(LongTermMemory, "clear")
        assert hasattr(LongTermMemory, "search")

    def test_conversation_memory_interface(self) -> None:
        assert hasattr(ConversationMemory, "add")
        assert hasattr(ConversationMemory, "get")
        assert hasattr(ConversationMemory, "clear")
        assert hasattr(ConversationMemory, "get_history")
        assert hasattr(ConversationMemory, "add_message")
        assert hasattr(ConversationMemory, "clear_session")


# ---------------------------------------------------------------------------
# 5.  Security interface
# ---------------------------------------------------------------------------

class TestPermissionGuardInterface:
    """PermissionGuard must define the security contract."""

    def test_interface_exists(self) -> None:
        assert hasattr(PermissionGuard, "can_access_document")


# ---------------------------------------------------------------------------
# 6.  Reranker interface
# ---------------------------------------------------------------------------

class TestRerankerInterface:
    """BaseReranker must define the reranking contract."""

    def test_interface_exists(self) -> None:
        assert hasattr(BaseReranker, "rerank")
        assert hasattr(BaseReranker, "score")


# ---------------------------------------------------------------------------
# 7.  Dependency-injection registry
# ---------------------------------------------------------------------------

class TestDependencyInjection:
    """DI functions must exist and return the expected types."""

    def test_get_knowledge_agent_returns_knowledge_agent(self) -> None:
        agent = get_knowledge_agent()
        assert isinstance(agent, KnowledgeAgent)

    def test_get_planner_agent_returns_planner_agent(self) -> None:
        agent = get_planner_agent()
        assert isinstance(agent, PlannerAgent)

    def test_get_finance_agent_returns_finance_agent(self) -> None:
        agent = get_finance_agent()
        assert isinstance(agent, FinanceAgent)

    def test_get_meeting_agent_returns_meeting_agent(self) -> None:
        agent = get_meeting_agent()
        assert isinstance(agent, MeetingAgent)

    def test_get_task_agent_returns_task_agent(self) -> None:
        agent = get_task_agent()
        assert isinstance(agent, TaskAgent)

    def test_get_notification_agent_returns_notification_agent(self) -> None:
        agent = get_notification_agent()
        assert isinstance(agent, NotificationAgent)

    def test_get_recommendation_agent_returns_recommendation_agent(self) -> None:
        agent = get_recommendation_agent()
        assert isinstance(agent, RecommendationAgent)

    def test_get_agent_map_covers_all_categories(self) -> None:
        agent_map = get_agent_map()
        for cat in RequestCategory:
            assert cat in agent_map, f"RequestCategory.{cat.name} missing from agent_map"
            assert isinstance(agent_map[cat], BaseAgent)

    def test_get_memory_manager_returns_memory_manager(self) -> None:
        mgr = get_memory_manager()
        assert isinstance(mgr, MemoryManager)


# ---------------------------------------------------------------------------
# 8.  Regression: existing architecture unchanged
# ---------------------------------------------------------------------------

class TestRegression:
    """The original execution contract must still hold."""

    @pytest.mark.asyncio
    async def test_orchestrator_accepts_pipeline_only(
        self, pipeline: ExecutionPipeline
    ) -> None:
        """Backward compat: AIOrchestrator(pipeline=pipeline) still works."""
        orch = AIOrchestrator(pipeline=pipeline)
        ctx = ExecutionContext(message="Hello")
        result = await orch.route_request(ctx)
        assert result == "fake:Hello"

    def test_request_category_has_original_members(self) -> None:
        """All original categories still exist."""
        assert RequestCategory.GENERAL_CHAT
        assert RequestCategory.COMPANY_KNOWLEDGE
        assert RequestCategory.DOCUMENT_QUERY
        assert RequestCategory.DOCUMENT_UPLOAD
        assert RequestCategory.IMAGE_ANALYSIS
        assert RequestCategory.MEETING
        assert RequestCategory.TASK_ASSISTANT
        assert RequestCategory.UNKNOWN

    def test_new_categories_exist(self) -> None:
        assert RequestCategory.FINANCE
        assert RequestCategory.RECOMMENDATION
