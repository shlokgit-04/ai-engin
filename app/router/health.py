from app.schemas.health import HealthResponse
from app.services.health import HealthService
from app.core.logging import logger


class HealthRouter:
    def __init__(self, service: HealthService) -> None:
        self._service = service

    async def check(self) -> HealthResponse:
        logger.info("Health check requested")
        return await self._service.check()
