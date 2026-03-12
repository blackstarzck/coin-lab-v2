from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.market import CandlePointResponse


class MonitoringSnapshotMessage(BaseModel):
    type: Literal["monitoring_snapshot"] = "monitoring_snapshot"
    trace_id: str
    timestamp: datetime
    data: dict[str, object]


class HeartbeatMessage(BaseModel):
    type: Literal["heartbeat"] = "heartbeat"
    trace_id: str
    timestamp: datetime


class ChartSnapshotMessage(BaseModel):
    type: Literal["chart_snapshot"] = "chart_snapshot"
    trace_id: str
    symbol: str
    timeframe: str
    points: list[CandlePointResponse]


class ChartPointMessage(BaseModel):
    type: Literal["chart_point"] = "chart_point"
    trace_id: str
    symbol: str
    timeframe: str
    point: CandlePointResponse
