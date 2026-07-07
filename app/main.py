from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.health import router as health_router
from app.api.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(
        "Starting Nurofin Executive AI Engine",
        version=settings.app_version,
    )
    yield
    logger.info("Shutting down Nurofin Executive AI Engine")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
