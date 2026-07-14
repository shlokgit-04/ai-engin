from typing import Literal
from pydantic import BaseModel


class ProviderHealthInfo(BaseModel):
    status: Literal["healthy", "unreachable"]
    message: str = ""


class ModelsHealthResponse(BaseModel):
    openrouter: ProviderHealthInfo | None = None
    ollama: ProviderHealthInfo | None = None
    gemini: Literal["healthy", "unreachable"] = "unreachable"
    active_provider: str = ""
