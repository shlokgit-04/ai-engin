import json
from typing import AsyncIterator

import httpx
from httpx import ConnectError, TimeoutException

from app.models.providers.base import AIProvider, ProviderHealth
from app.core.logging import logger


class OllamaProvider(AIProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        logger.info("OllamaProvider initialized", base_url=base_url, model=model)

    @property
    def provider_name(self) -> str:
        return "ollama"

    def list_models(self) -> list[str]:
        return [
            "llama3",
            "llama3.1",
            "llama3.2",
            "mistral",
            "mixtral",
            "codellama",
            "gemma2",
            "qwen2.5",
            "phi3",
            "deepseek-r1",
        ]

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except ConnectError as e:
            raise RuntimeError(f"Ollama connection failed: {e}") from e
        except TimeoutException as e:
            raise RuntimeError(f"Ollama request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama HTTP {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed: {e}") from e

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/generate",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                            text = chunk.get("response", "")
                            if text:
                                yield text
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
        except ConnectError as e:
            raise RuntimeError(f"Ollama connection failed: {e}") from e
        except TimeoutException as e:
            raise RuntimeError(f"Ollama streaming timed out: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama streaming failed: {e}") from e

    async def health_check(self) -> ProviderHealth:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                return ProviderHealth(healthy=True, provider="ollama")
        except Exception as e:
            return ProviderHealth(healthy=False, provider="ollama", message=str(e))
