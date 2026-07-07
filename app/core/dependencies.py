from app.core.config import settings
from app.core.exceptions import ConfigurationError
from app.models.gemini import GeminiClient
from app.services.health import HealthService
from app.services.chat import ChatService
from app.router.health import HealthRouter
from app.router.chat import ChatRouter
from app.agents.chat_agent import ChatAgent
from app.memory.chat_memory import ChatMemory
from app.memory.base import BaseMemory


def get_gemini_client() -> GeminiClient:
    if not settings.gemini_api_key:
        raise ConfigurationError(
            "Gemini API key is missing. Please configure GEMINI_API_KEY in the .env file."
        )
    return GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
    )


def get_chat_agent() -> ChatAgent:
    return ChatAgent(model_client=get_gemini_client())


def get_health_service() -> HealthService:
    return HealthService()


def get_chat_service() -> ChatService:
    return ChatService(
        agent=get_chat_agent(),
        memory=get_chat_memory(),
    )


def get_chat_memory() -> BaseMemory:
    return ChatMemory()


def get_health_router() -> HealthRouter:
    return HealthRouter(service=get_health_service())


def get_chat_router() -> ChatRouter:
    return ChatRouter(service=get_chat_service())
