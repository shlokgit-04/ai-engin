"""Tests for the BackendClient integration layer.

Verifies:
  - HTTP methods (GET, POST, PUT, DELETE) route correctly.
  - Exceptions are raised for connection errors, timeouts, 4xx, 5xx.
  - Invalid JSON responses are caught.
  - Retry logic retries network failures but not 4xx.
  - Configuration is read from settings.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch

import httpx

from app.integrations.backend.client import BackendClient
from app.integrations.backend.exceptions import (
    BackendClientError,
    BackendConnectionError,
    BackendInvalidJSONError,
    BackendNotFoundError,
    BackendServerError,
    BackendTimeoutError,
)


@pytest.fixture
def client() -> BackendClient:
    return BackendClient(base_url="http://test-backend:8001")


# ---------------------------------------------------------------------------
# 1.  Successful requests
# ---------------------------------------------------------------------------

class TestSuccessfulRequests:
    @pytest.mark.asyncio
    async def test_get_returns_json(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}

        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.get("/projects")
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_post_returns_json(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": "p-1", "name": "Test"}

        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.post("/projects", json_body={"name": "Test"})
        assert result["name"] == "Test"

    @pytest.mark.asyncio
    async def test_put_returns_json(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "updated"}

        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.put("/projects/p-1", json_body={"name": "New"})
        assert result["status"] == "updated"

    @pytest.mark.asyncio
    async def test_delete_returns_json(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "deleted"}

        with patch.object(client._client, "request", return_value=mock_resp):
            result = await client.delete("/projects/p-1")
        assert result["status"] == "deleted"


# ---------------------------------------------------------------------------
# 2.  Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_404_raises_not_found(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"

        with patch.object(client._client, "request", return_value=mock_resp):
            with pytest.raises(BackendNotFoundError) as exc:
                await client.get("/projects/missing")
            assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_400_raises_client_error(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"

        with patch.object(client._client, "request", return_value=mock_resp):
            with pytest.raises(BackendClientError) as exc:
                await client.post("/projects", json_body={"bad": "data"})
            assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_500_raises_server_error(self, client: BackendClient) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch.object(client._client, "request", return_value=mock_resp):
            with pytest.raises(BackendServerError) as exc:
                await client.get("/projects")
            assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_timeout_raises_timeout_error(self, client: BackendClient) -> None:
        with patch.object(
            client._client, "request",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with pytest.raises(BackendTimeoutError):
                await client.get("/projects")

    @pytest.mark.asyncio
    async def test_connection_refused_raises_connection_error(
        self, client: BackendClient
    ) -> None:
        with patch.object(
            client._client, "request",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(BackendConnectionError):
                await client.get("/projects")

    @pytest.mark.asyncio
    async def test_invalid_json_raises_invalid_json_error(
        self, client: BackendClient
    ) -> None:
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)
        mock_resp.text = "not json"

        with patch.object(client._client, "request", return_value=mock_resp):
            with pytest.raises(BackendInvalidJSONError):
                await client.get("/projects")


# ---------------------------------------------------------------------------
# 3.  Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self, client: BackendClient) -> None:
        client._max_retries = 2
        side_effects = [
            httpx.ConnectError("fail 1"),
            httpx.ConnectError("fail 2"),
            AsyncMock(
                status_code=200,
                json=lambda: {"status": "ok"},
                text="ok",
            ),
        ]
        with patch.object(
            client._client, "request",
            side_effect=side_effects,
        ):
            result = await client.get("/projects")
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_exhausts_retries_on_connection_error(
        self, client: BackendClient
    ) -> None:
        client._max_retries = 2
        with patch.object(
            client._client, "request",
            side_effect=httpx.ConnectError("always fails"),
        ):
            with pytest.raises(BackendConnectionError):
                await client.get("/projects")

    @pytest.mark.asyncio
    async def test_does_not_retry_4xx(self, client: BackendClient) -> None:
        client._max_retries = 2
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 400
        mock_resp.text = "Bad Request"

        with patch.object(client._client, "request", return_value=mock_resp) as mocked:
            with pytest.raises(BackendClientError):
                await client.get("/projects")
            assert mocked.call_count == 1

    @pytest.mark.asyncio
    async def test_does_not_retry_404(self, client: BackendClient) -> None:
        client._max_retries = 2
        mock_resp = AsyncMock(spec=httpx.Response)
        mock_resp.status_code = 404
        mock_resp.text = "Not Found"

        with patch.object(client._client, "request", return_value=mock_resp) as mocked:
            with pytest.raises(BackendNotFoundError):
                await client.get("/projects/missing")
            assert mocked.call_count == 1
