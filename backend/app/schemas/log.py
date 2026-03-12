from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LogEntryResponse(BaseModel):
    id: str
    channel: str
    level: str
    trace_id: str | None = None
    mode: str | None = None
    session_id: str | None = None
    strategy_version_id: str | None = None
    symbol: str | None = None
    event_type: str
    message: str
    payload: dict[str, object] = Field(default_factory=dict)
    logged_at: datetime
