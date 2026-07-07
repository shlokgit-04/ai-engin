import logging
import structlog
from app.core.config import settings


def setup_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")


logger = structlog.get_logger()
