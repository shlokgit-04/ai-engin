from typing import Any


class BackendError(Exception):
    """Base exception for all backend integration errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class BackendConnectionError(BackendError):
    """Raised when the client cannot connect to the backend."""


class BackendTimeoutError(BackendError):
    """Raised when a request to the backend times out."""


class BackendNotFoundError(BackendError):
    """Raised when the backend returns a 404."""


class BackendServerError(BackendError):
    """Raised when the backend returns a 5xx."""


class BackendClientError(BackendError):
    """Raised when the backend returns a 4xx (excluding 404)."""


class BackendInvalidJSONError(BackendError):
    """Raised when the backend returns invalid JSON."""
