from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_models_health_router
from app.router.health_models import ModelsHealthRouter
from app.services.health_models import ModelsHealthService
from app.models.base import BaseLLM


class HealthyFakeLLM(BaseLLM):
    async def generate_response(self, prompt: str, **kwargs) -> str:
        return "ok"

    async def health_check(self) -> bool:
        return True


class UnhealthyFakeLLM(BaseLLM):
    async def generate_response(self, prompt: str, **kwargs) -> str:
        return "ok"

    async def health_check(self) -> bool:
        return False


def test_models_health_all_healthy():
    gemini = HealthyFakeLLM()
    ollama = HealthyFakeLLM()
    service = ModelsHealthService(gemini=gemini, ollama=ollama)
    router = ModelsHealthRouter(service=service)

    app.dependency_overrides[get_models_health_router] = lambda: router
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/models")
        assert response.status_code == 200
        assert response.json() == {"gemini": "healthy", "ollama": "healthy"}
    finally:
        app.dependency_overrides.clear()


def test_models_health_ollama_down():
    gemini = HealthyFakeLLM()
    ollama = UnhealthyFakeLLM()
    service = ModelsHealthService(gemini=gemini, ollama=ollama)
    router = ModelsHealthRouter(service=service)

    app.dependency_overrides[get_models_health_router] = lambda: router
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/models")
        assert response.status_code == 200
        assert response.json() == {"gemini": "healthy", "ollama": "unreachable"}
    finally:
        app.dependency_overrides.clear()


def test_models_health_both_down():
    gemini = UnhealthyFakeLLM()
    ollama = UnhealthyFakeLLM()
    service = ModelsHealthService(gemini=gemini, ollama=ollama)
    router = ModelsHealthRouter(service=service)

    app.dependency_overrides[get_models_health_router] = lambda: router
    try:
        client = TestClient(app)
        response = client.get("/api/v1/health/models")
        assert response.status_code == 200
        assert response.json() == {"gemini": "unreachable", "ollama": "unreachable"}
    finally:
        app.dependency_overrides.clear()
