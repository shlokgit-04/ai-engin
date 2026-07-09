from fastapi import APIRouter, Depends
from app.schemas.health_models import ModelsHealthResponse
from app.router.health_models import ModelsHealthRouter
from app.core.dependencies import get_models_health_router

router = APIRouter(tags=["Health"])


@router.get("/health/models", response_model=ModelsHealthResponse)
async def models_health(
    router: ModelsHealthRouter = Depends(get_models_health_router),
) -> ModelsHealthResponse:
    return await router.check()
