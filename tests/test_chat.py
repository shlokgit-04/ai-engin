from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_chat_router
from app.router.chat import ChatRouter
from app.services.chat import ChatService
from app.agents.chat_agent import ChatAgent


class FakeGeminiClient:
    async def generate_response(self, prompt: str, **kwargs) -> str:
        return "Hello from Nurofin Executive AI Engine"

    async def health_check(self) -> bool:
        return True


def test_chat_endpoint():
    fake_client = FakeGeminiClient()
    agent = ChatAgent(model_client=fake_client)
    service = ChatService(agent=agent)
    router = ChatRouter(service=service)

    app.dependency_overrides[get_chat_router] = lambda: router

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"},
        )
        assert response.status_code == 200
        assert response.json() == {"response": "Hello from Nurofin Executive AI Engine"}
    finally:
        app.dependency_overrides.clear()
