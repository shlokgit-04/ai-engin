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
        return (time.monotonic() - self.exhausted_at) > 300

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
        valid_keys = [k.strip() for k in api_keys if k and k.strip()]
        if not valid_keys:
            raise ValueError(
                "OpenRouter requires at least one valid API key. "
                "Configure OPENROUTER_API_KEY_1 through OPENROUTER_API_KEY_10."
            )
        self._keys = [KeyState(k) for k in valid_keys]
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._current_idx = 0
        logger.info(
            "OpenRouterProvider initialized",
            key_count=len(self._keys),
            model=model,
        )

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

    def _next_key(self) -> KeyState | None:
        """Find the next available key, starting from _current_idx."""
        start = self._current_idx
        n = len(self._keys)
        for i in range(n):
            idx = (start + i) % n
            if self._keys[idx].is_available:
                self._current_idx = idx
                return self._keys[idx]
        return None

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
        system_prompt: str | None,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> dict:
        messages = []
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

        for _attempt in range(len(self._keys)):
            key_state = self._next_key()
            if key_state is None:
                logger.error("All OpenRouter API keys exhausted")
                break

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
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    if content:
                        return content
                    last_error = Exception("Empty response from OpenRouter")
                    continue

                if response.status_code in _OPENROUTER_RETRYABLE:
                    logger.warning(
                        "OpenRouter retryable error",
                        status=response.status_code,
                        key_index=self._current_idx,
                    )
                    key_state.mark_exhausted()
                    last_error = Exception(f"OpenRouter HTTP {response.status_code}")
                    continue

                logger.error(
                    "OpenRouter non-retryable error",
                    status=response.status_code,
                    body=response.text[:200],
                )
                last_error = Exception(f"OpenRouter HTTP {response.status_code}: {response.text[:200]}")
                break

            except httpx.TimeoutException:
                logger.warning("OpenRouter timeout", key_index=self._current_idx)
                key_state.mark_exhausted()
                last_error = Exception("OpenRouter request timed out")
                continue
            except httpx.ConnectError as e:
                logger.warning("OpenRouter connection error", error=str(e))
                last_error = e
                break
            except Exception as e:
                logger.error("OpenRouter unexpected error", error=str(e))
                last_error = e
                break

        msg = str(last_error) if last_error else "All OpenRouter keys exhausted"
        raise RuntimeError(f"OpenRouter provider failed: {msg}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        key_state = self._next_key()
        if key_state is None:
            raise RuntimeError("All OpenRouter API keys exhausted")

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
                            raise RuntimeError(f"OpenRouter streaming HTTP {response.status_code}")
                        raise RuntimeError(f"OpenRouter streaming HTTP {response.status_code}: {body[:200]}")

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content", "")
                            if text:
                                yield text
                        except Exception:
                            continue
        except httpx.TimeoutException:
            key_state.mark_exhausted()
            raise RuntimeError("OpenRouter streaming timed out")
        except httpx.ConnectError as e:
            raise RuntimeError(f"OpenRouter connection failed: {e}")

    async def health_check(self) -> ProviderHealth:
        key_state = self._next_key()
        if key_state is None:
            return ProviderHealth(healthy=False, provider="openrouter", message="No API keys available")
        try:
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
            return ProviderHealth(
                healthy=False,
                provider="openrouter",
                message=f"HTTP {response.status_code}",
            )
        except Exception as e:
            return ProviderHealth(healthy=False, provider="openrouter", message=str(e))
