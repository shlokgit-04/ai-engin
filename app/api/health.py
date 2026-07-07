from fastapi import APIRouter, Depends
from app.schemas.health import HealthResponse
from app.router.health import HealthRouter
from app.core.dependencies import get_health_router

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    health_router: HealthRouter = Depends(get_health_router),
) -> HealthResponse:
    return await health_router.check()
