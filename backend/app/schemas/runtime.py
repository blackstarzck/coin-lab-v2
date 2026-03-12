from __future__ import annotations

from pydantic import BaseModel


class RuntimeStatusResponse(BaseModel):
    running: bool
    store_backend: str
    session_count: int
    running_session_count: int
