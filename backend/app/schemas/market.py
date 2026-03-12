from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CandlePointResponse(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class ChartSnapshotResponse(BaseModel):
    symbol: str
    timeframe: str
    points: list[CandlePointResponse]


class ChartPointResponse(BaseModel):
    symbol: str
    timeframe: str
    point: CandlePointResponse
