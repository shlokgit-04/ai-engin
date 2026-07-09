import httpx
from httpx import ConnectError, TimeoutException

from app.models.base import BaseLLM
from app.core.logging import logger
from app.core.exceptions import ModelError


class OllamaClient(BaseLLM):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        logger.info("OllamaClient initialized", base_url=base_url, model=model)

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        logger.debug(
            "Generating Ollama response",
            model=self._model,
            prompt_length=len(prompt),
        )
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
            logger.error("Ollama connection failed", error=str(e))
            raise ModelError(f"Ollama connection failed: {e}", model=self._model) from e
        except TimeoutException as e:
            logger.error("Ollama request timed out", error=str(e))
            raise ModelError(f"Ollama request timed out: {e}", model=self._model) from e
        except httpx.HTTPStatusError as e:
            logger.error(
                "Ollama HTTP error",
                status_code=e.response.status_code,
                body=e.response.text,
            )
            raise ModelError(
                f"Ollama HTTP {e.response.status_code}: {e.response.text}",
                model=self._model,
            ) from e
        except Exception as e:
            logger.error("Ollama generation failed", error=str(e))
            raise ModelError(f"Ollama generation failed: {e}", model=self._model) from e

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error("Ollama health check failed", error=str(e))
            return False
