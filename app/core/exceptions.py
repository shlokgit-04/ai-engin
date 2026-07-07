class NurofinError(Exception):
    """Base exception for all Nurofin AI Engine errors."""


class ServiceError(NurofinError):
    """Raised when a service encounters an error."""

    def __init__(self, message: str, service: str | None = None) -> None:
        self.service = service
        super().__init__(message)


class AgentError(NurofinError):
    """Raised when an agent encounters an error."""

    def __init__(self, message: str, agent: str | None = None) -> None:
        self.agent = agent
        super().__init__(message)


class ConfigurationError(NurofinError):
    """Raised when there is a configuration error."""


class ModelError(NurofinError):
    """Raised when an AI model encounters an error."""

    def __init__(self, message: str, model: str | None = None) -> None:
        self.model = model
        super().__init__(message)
