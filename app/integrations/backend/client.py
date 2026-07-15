import json
import time
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.integrations.backend.config import BackendConfig
from app.integrations.backend.exceptions import (
    BackendClientError,
    BackendConnectionError,
    BackendInvalidJSONError,
    BackendNotFoundError,
    BackendServerError,
    BackendTimeoutError,
)


class BackendClient:
    """Reusable async HTTP client for the Nurofin backend.

    Uses ``httpx.AsyncClient`` under the hood.  Exposes convenience
    ``GET`` / ``POST`` / ``PUT`` / ``DELETE`` methods that all go
    through a single ``_request`` funnel for logging, error mapping,
    and retry logic.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        config = BackendConfig()
        self._base_url = (base_url or config.base_url).rstrip("/")
        self._timeout = timeout or config.timeout
        self._max_retries = max_retries or config.max_retries
        self._client = httpx.AsyncClient(timeout=self._timeout, follow_redirects=True)

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json_body: dict[str, Any] | None = None, auth_token: str | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("POST", path, body=json_body, params=params)

    async def put(self, path: str, json_body: dict[str, Any] | None = None, auth_token: str | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("PUT", path, body=json_body, params=params)

    async def delete(self, path: str, auth_token: str | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._request("DELETE", path, params=params)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=body,
                )
            except httpx.TimeoutException as exc:
                logger.warning("Backend timeout", path=path, attempt=attempt)
                last_exc = BackendTimeoutError(
                    f"Request timed out after {self._timeout}s: {method} {path}",
                )
                if attempt < self._max_retries:
                    continue
                raise last_exc
            except httpx.ConnectError as exc:
                logger.warning("Backend connection failed", path=path, attempt=attempt)
                last_exc = BackendConnectionError(
                    f"Cannot connect to backend at {self._base_url}: {exc}",
                )
                if attempt < self._max_retries:
                    continue
                raise last_exc
            except httpx.HTTPError as exc:
                raise BackendConnectionError(
                    f"HTTP error during request: {exc}",
                )

            elapsed = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "Backend request",
                method=method,
                path=path,
                status_code=response.status_code,
                elapsed_ms=elapsed,
            )

            if response.status_code == 404:
                raise BackendNotFoundError(
                    f"Resource not found: {method} {path}",
                    status_code=404,
                    response_body=response.text,
                )

            if 400 <= response.status_code < 500:
                raise BackendClientError(
                    f"Client error: {method} {path} returned {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            if response.status_code >= 500:
                raise BackendServerError(
                    f"Server error: {method} {path} returned {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            try:
                return response.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise BackendInvalidJSONError(
                    f"Invalid JSON in response: {exc}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

        # Should not reach here, but satisfy type-checker.
        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        await self._client.aclose()
