from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_models_health_router
from app.router.health_models import ModelsHealthRouter
from app.services.health_models import ModelsHealthService
from app.models.base import BaseLLM
from app.models.providers.base import ProviderHealth
from app.models.providers.manager import ProviderManager
from app.models.providers.base import ProviderHealth


class _FakeProvider:
    provider_name = "fake"
    current_model = "fake-model"

    def __init__(self, healthy: bool = True):
        self._healthy = healthy

    async def generate(self, prompt, **kwargs):
        return "ok"

    async def generate_stream(self, prompt, **kwargs):
        yield "ok"

    async def health_check(self):
        return ProviderHealth(healthy=self._healthy, provider="fake", message="ok" if self._healthy else "down")

    def list_models(self):
        return []


class HealthyFakeLLM(BaseLLM):
    async def generate_response(self, prompt: str, **kwargs) -> str:
        return "ok"

    async def health_check(self) -> bool:
        return True


def test_models_health_all_healthy():
    gemini = HealthyFakeLLM()
    pm = ProviderManager(providers={"fake": _FakeProvider(healthy=True)}, default_provider="fake")
    service = ModelsHealthService(provider_manager=pm, gemini=gemini)
    router = ModelsHealthRouter(service=service)

    app.dependency_overrides[get_models_health_router] = lambda: router
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/models")
        assert response.status_code == 200
        data = response.json()
        assert data["gemini"] == "healthy"
    finally:
        app.dependency_overrides.clear()


def test_models_health_provider_unhealthy():
    gemini = HealthyFakeLLM()
    pm = ProviderManager(providers={"fake": _FakeProvider(healthy=False)}, default_provider="fake")
    service = ModelsHealthService(provider_manager=pm, gemini=gemini)
    router = ModelsHealthRouter(service=service)

    app.dependency_overrides[get_models_health_router] = lambda: router
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/models")
        assert response.status_code == 200
        data = response.json()
        assert data["gemini"] == "healthy"
    finally:
        app.dependency_overrides.clear()
