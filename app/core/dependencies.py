from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.core.logging import logger
from app.models.gemini import GeminiClient
from app.models.ollama import OllamaClient
from app.models.providers.openrouter import OpenRouterProvider
from app.models.providers.ollama_provider import OllamaProvider
from app.models.providers.manager import ProviderManager
from app.models.provider_manager_llm import ProviderManagerLLM
from app.orchestrator.orchestrator import AIOrchestrator
from app.orchestrator.pipeline import ExecutionPipeline
from app.orchestrator.enums import RequestCategory
from app.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.services.health import HealthService
from app.services.chat import ChatService
from app.services.health_models import ModelsHealthService
from app.router.health import HealthRouter
from app.router.chat import ChatRouter
from app.router.health_models import ModelsHealthRouter
from app.agents.base import BaseAgent
from app.agents.chat_agent import ChatAgent
from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.finance_agent import FinanceAgent
from app.agents.meeting_agent import MeetingAgent
from app.agents.task_agent import TaskAgent
from app.agents.notification_agent import NotificationAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.memory.base import BaseMemory
from app.memory.chat_memory import ChatMemory
from app.memory.manager import MemoryManager
from app.security.permission_guard import PermissionGuard
from app.tools.router import ToolRouter
from app.tools.project_tool import ProjectTool
from app.tools.task_tool import TaskTool
from app.tools.planner_tool import PlannerTool
from app.tools.notification_tool import NotificationTool
from app.tools.dashboard_tool import DashboardTool
from app.tools.executive_tool import ExecutiveTool
from app.integrations.backend.client import BackendClient


_provider_manager_instance: ProviderManager | None = None


def get_backend_client() -> BackendClient:
    return BackendClient()


def get_provider_manager() -> ProviderManager:
    global _provider_manager_instance
    if _provider_manager_instance is not None:
        return _provider_manager_instance

    providers: dict = {}

    openrouter_keys = settings.openrouter_keys
    if openrouter_keys:
        try:
            providers["openrouter"] = OpenRouterProvider(
                api_keys=openrouter_keys,
                model=settings.openrouter_model,
            )
        except Exception as e:
            logger.warning("Failed to initialize OpenRouter provider", error=str(e))

    try:
        providers["ollama"] = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
    except Exception as e:
        logger.warning("Failed to initialize Ollama provider", error=str(e))

    default = settings.default_provider if settings.default_provider in providers else next(iter(providers), None)
    if not providers:
        raise ConfigurationError("No AI providers could be configured.")

    _provider_manager_instance = ProviderManager(providers=providers, default_provider=default)
    return _provider_manager_instance


def get_gemini_client() -> GeminiClient:
    if not settings.gemini_api_key:
        raise ConfigurationError(
            "Gemini API key is missing. Please configure GEMINI_API_KEY in the .env file."
        )
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )


def get_ollama_client() -> OllamaClient:
    return OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )


def get_knowledge_pipeline() -> DocumentIntelligencePipeline:
    return DocumentIntelligencePipeline()


def get_execution_pipeline() -> ExecutionPipeline:
    provider_llm = None
    try:
        manager = get_provider_manager()
        provider_llm = ProviderManagerLLM(manager)
    except Exception as e:
        logger.warning("Could not initialize ProviderManager for pipeline", error=str(e))

    return ExecutionPipeline(
        gemini=get_gemini_client(),
        ollama=get_ollama_client(),
        knowledge_pipeline=get_knowledge_pipeline(),
        provider_llm=provider_llm,
    )


def get_tool_router() -> ToolRouter:
    router = ToolRouter()
    router.register(ExecutiveTool())
    return router


def get_knowledge_agent() -> KnowledgeAgent:
    return KnowledgeAgent(pipeline=get_execution_pipeline())


def get_planner_agent() -> PlannerAgent:
    return PlannerAgent()


def get_finance_agent() -> FinanceAgent:
    return FinanceAgent()


def get_meeting_agent() -> MeetingAgent:
    return MeetingAgent()


def get_task_agent() -> TaskAgent:
    return TaskAgent()


def get_notification_agent() -> NotificationAgent:
    return NotificationAgent()


def get_recommendation_agent() -> RecommendationAgent:
    return RecommendationAgent()


def get_agent_map() -> dict[RequestCategory, BaseAgent]:
    return {
        RequestCategory.GENERAL_CHAT: get_knowledge_agent(),
        RequestCategory.COMPANY_KNOWLEDGE: get_knowledge_agent(),
        RequestCategory.DOCUMENT_QUERY: get_knowledge_agent(),
        RequestCategory.DOCUMENT_UPLOAD: get_planner_agent(),
        RequestCategory.IMAGE_ANALYSIS: get_planner_agent(),
        RequestCategory.MEETING: get_meeting_agent(),
        RequestCategory.TASK_ASSISTANT: get_task_agent(),
        RequestCategory.FINANCE: get_finance_agent(),
        RequestCategory.RECOMMENDATION: get_recommendation_agent(),
        RequestCategory.UNKNOWN: get_knowledge_agent(),
    }


def get_orchestrator() -> AIOrchestrator:
    return AIOrchestrator(
        pipeline=get_execution_pipeline(),
        agents=get_agent_map(),
        tool_router=get_tool_router(),
    )


def get_chat_agent() -> ChatAgent:
    return ChatAgent(orchestrator=get_orchestrator())


def get_memory_manager() -> MemoryManager:
    return MemoryManager()


def get_permission_guard() -> PermissionGuard:
    raise NotImplementedError("PermissionGuard implementation not yet available.")


def get_health_service() -> HealthService:
    return HealthService()


def get_chat_service() -> ChatService:
    return ChatService(
        agent=get_chat_agent(),
        memory=get_chat_memory(),
    )


def get_models_health_service() -> ModelsHealthService:
    return ModelsHealthService(
        gemini=get_gemini_client(),
        ollama=get_ollama_client(),
    )


def get_chat_memory() -> BaseMemory:
    return ChatMemory()


def get_health_router() -> HealthRouter:
    return HealthRouter(service=get_health_service())


def get_chat_router() -> ChatRouter:
    return ChatRouter(service=get_chat_service())


def get_models_health_router() -> ModelsHealthRouter:
    return ModelsHealthRouter(service=get_models_health_service())
