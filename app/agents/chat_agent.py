from app.agents.base import BaseAgent
from app.models.gemini import GeminiClient
from app.prompts.chat import SYSTEM_PROMPT, DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS
from app.core.logging import logger


class ChatAgent(BaseAgent):
    def __init__(self, model_client: GeminiClient) -> None:
        self._client = model_client

    async def run(self, input: str, **kwargs) -> str:
        logger.info("ChatAgent processing", input_length=len(input))
        response = await self._client.generate_response(
            prompt=input,
            system_prompt=SYSTEM_PROMPT,
            temperature=kwargs.get("temperature", DEFAULT_TEMPERATURE),
            max_tokens=kwargs.get("max_tokens", DEFAULT_MAX_TOKENS),
        )
        return response
