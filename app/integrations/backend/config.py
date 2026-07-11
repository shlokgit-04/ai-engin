from dataclasses import dataclass, field
from app.core.config import settings


@dataclass
class BackendConfig:
    base_url: str = field(default_factory=lambda: settings.backend_base_url)
    timeout: float = 30.0
    max_retries: int = 2
