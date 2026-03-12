from __future__ import annotations

from pydantic import BaseModel


class ExecutionStatusResponse(BaseModel):
    accepted: bool
    message: str
