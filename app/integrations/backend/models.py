from pydantic import BaseModel
from typing import Any


class StatusResponse(BaseModel):
    status: str
    message: str
