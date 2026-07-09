from app.schemas.health_models import ModelsHealthResponse
from app.services.health_models import ModelsHealthService
from app.core.logging import logger


class ModelsHealthRouter:
    def __init__(self, service: ModelsHealthService) -> None:
        self._service = service

    async def check(self) -> ModelsHealthResponse:
        logger.info("Models health check routed")
        return await self._service.check()
