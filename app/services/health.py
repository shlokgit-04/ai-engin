from app.schemas.health import HealthResponse
from app.core.logging import logger


class HealthService:
    async def check(self) -> HealthResponse:
        logger.debug("Health service invoked")
        return HealthResponse(status="healthy")
