from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors

from app.core.logging import logger
from app.core.exceptions import ModelError


class GeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self._model = model
        self._client = genai.Client(api_key=api_key)
        logger.info("GeminiClient initialized", model=model)

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        logger.debug(
            "Generating Gemini response",
            model=self._model,
            prompt_length=len(prompt),
        )
        try:
            config = genai_types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
            if system_prompt:
                config.system_instruction = system_prompt

            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=config,
            )
            return response.text
        except genai_errors.ClientError as e:
            logger.error("Gemini API client error", error=str(e), code=e.code)
            raise ModelError(f"Gemini API error: {e}", model=self._model) from e
        except Exception as e:
            logger.error("Gemini generation failed", error=str(e))
            raise ModelError(f"Gemini generation failed: {e}", model=self._model) from e

    async def health_check(self) -> bool:
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents="Respond with a single word: OK",
            )
            return bool(response.text)
        except Exception as e:
            logger.error("Gemini health check failed", error=str(e))
            return False
