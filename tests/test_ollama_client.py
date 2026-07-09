import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.ollama import OllamaClient
from app.core.exceptions import ModelError


@pytest.fixture
def ollama_client():
    return OllamaClient(base_url="http://test:11434", model="test-model")


@pytest.mark.asyncio
async def test_generate_response_success(ollama_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "Hello!", "done": True}
    mock_resp.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await ollama_client.generate_response("Hello")
        assert result == "Hello!"


@pytest.mark.asyncio
async def test_generate_response_with_system_prompt(ollama_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "I am helpful.", "done": True}
    mock_resp.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await ollama_client.generate_response(
            "Hi",
            system_prompt="You are helpful.",
            temperature=0.5,
            max_tokens=100,
        )
        assert result == "I am helpful."

    call_kwargs = mock_client.post.call_args
    payload = call_kwargs[1]["json"]
    assert payload["system"] == "You are helpful."
    assert payload["options"]["temperature"] == 0.5
    assert payload["options"]["num_predict"] == 100


@pytest.mark.asyncio
async def test_generate_response_connection_error(ollama_client):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(side_effect=ConnectionError("refused"))

    with patch("httpx.AsyncClient", return_value=mock_client), pytest.raises(ModelError):
        await ollama_client.generate_response("Hello")


@pytest.mark.asyncio
async def test_generate_response_http_error(ollama_client):
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.text = "model not found"
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock_resp
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client), pytest.raises(ModelError):
        await ollama_client.generate_response("Hello")


@pytest.mark.asyncio
async def test_health_check_success(ollama_client):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await ollama_client.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_health_check_failure(ollama_client):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await ollama_client.health_check()
        assert result is False
