from typing import Literal
from pydantic import BaseModel


class ModelsHealthResponse(BaseModel):
    gemini: Literal["healthy", "unreachable"]
    ollama: Literal["healthy", "unreachable"]
