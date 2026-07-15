import time
import asyncio
from typing import AsyncIterator

import httpx

from app.models.providers.base import AIProvider, ProviderHealth
from app.core.logging import logger


class KeyState:
    __slots__ = ("key", "exhausted_at")

    def __init__(self, key: str) -> None:
        self.key = key
        self.exhausted_at: float | None = None

    @property
    def is_available(self) -> bool:
        if self.exhausted_at is None:
            return True
        return (time.monotonic() - self.exhausted_at) >= 300

    def mark_exhausted(self) -> None:
        self.exhausted_at = time.monotonic()

    def __repr__(self) -> str:
        masked = self.key[:8] + "..." + self.key[-4:] if len(self.key) > 12 else "***"
        return f"KeyState({masked}, exhausted={self.is_available})"


_OPENROUTER_RETRYABLE = (429, 502, 503, 504)


class OpenRouterProvider(AIProvider):
    def __init__(
        self,
        api_keys: list[str],
        model: str = "openai/gpt-oss-20b:free",
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 60.0,
    ) -> None:
        cleaned = [k.strip() for k in api_keys if k.strip()]
        if not cleaned:
            raise ValueError(
                "OpenRouter requires at least one valid API key. "
                "Configure OPENROUTER_API_KEY_1 through OPENROUTER_API_KEY_10."
            )
        self._keys = [KeyState(k) for k in cleaned]
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._current_idx = 0
        logger.info("OpenRouterProvider initialized", key_count=len(self._keys), model=model)

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def list_models(self) -> list[str]:
        return [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "openai/gpt-oss-20b:free",
            "anthropic/claude-sonnet-4",
            "anthropic/claude-3.5-haiku",
            "google/gemini-2.5-flash",
            "google/gemini-2.5-pro",
            "meta-llama/llama-4-maverick:free",
            "deepseek/deepseek-chat-v3-0324:free",
            "qwen/qwen3-235b-a22b:free",
        ]

    def _next_key(self) -> KeyState:
        """Find the next available key, starting from _current_idx."""
        for i in range(len(self._keys)):
            idx = (self._current_idx + i) % len(self._keys)
            if self._keys[idx].is_available:
                self._current_idx = (idx + 1) % len(self._keys)
                return self._keys[idx]
        raise RuntimeError("All OpenRouter API keys exhausted")

    def _build_headers(self, key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://nurofin.com",
            "X-Title": "Nurofin Executive AI",
        }

    def _build_payload(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> dict:
        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        last_error: Exception | None = None
        for _ in range(len(self._keys)):
            key_state = self._next_key()
            payload = self._build_payload(prompt, system_prompt, temperature, max_tokens, stream=False)
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/chat/completions",
                        headers=self._build_headers(key_state.key),
                        json=payload,
                    )
                    if response.status_code == 200:
                        data = response.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if not content:
                            raise RuntimeError("Empty response from OpenRouter")
                        return content
                    if response.status_code in _OPENROUTER_RETRYABLE:
                        logger.warning("OpenRouter retryable error", status=response.status_code, key_index=self._current_idx)
                        key_state.mark_exhausted()
                        continue
                    raise RuntimeError(f"OpenRouter HTTP {response.status_code}: {response.text}")
            except httpx.TimeoutException:
                last_error = RuntimeError("OpenRouter request timed out")
                logger.warning("OpenRouter timeout", key_index=self._current_idx)
                key_state.mark_exhausted()
                continue
            except httpx.ConnectError as exc:
                last_error = RuntimeError(f"OpenRouter connection error: {exc}")
                logger.warning("OpenRouter connection error", error=str(exc))
                raise last_error
            except RuntimeError:
                raise
            except Exception as exc:
                last_error = RuntimeError(f"OpenRouter unexpected error: {exc}")
                logger.error("OpenRouter unexpected error", error=str(exc))
                raise last_error
        raise RuntimeError(f"All OpenRouter keys exhausted. Last error: {last_error}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        key_state = self._next_key()
        payload = self._build_payload(prompt, system_prompt, temperature, max_tokens, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/chat/completions",
                    headers=self._build_headers(key_state.key),
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        if response.status_code in _OPENROUTER_RETRYABLE:
                            key_state.mark_exhausted()
                        raise RuntimeError(f"OpenRouter streaming HTTP {response.status_code}: {body.decode()}")
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, IndexError, KeyError):
                            continue
        except httpx.TimeoutException:
            key_state.mark_exhausted()
            raise RuntimeError("OpenRouter streaming timed out")
        except httpx.ConnectError as exc:
            raise RuntimeError(f"OpenRouter connection failed: {exc}")

    async def health_check(self) -> ProviderHealth:
        try:
            key_state = self._next_key()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._build_headers(key_state.key),
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": "Say OK"}],
                        "max_tokens": 5,
                    },
                )
                if response.status_code == 200:
                    return ProviderHealth(healthy=True, provider="openrouter")
                return ProviderHealth(healthy=False, provider="openrouter", message=f"HTTP {response.status_code}")
        except Exception as exc:
            return ProviderHealth(healthy=False, provider="openrouter", message=str(exc))
