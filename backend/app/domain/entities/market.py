from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EventType(StrEnum):
    TRADE_TICK = "TRADE_TICK"
    ORDERBOOK_SNAPSHOT = "ORDERBOOK_SNAPSHOT"
    CANDLE_UPDATE = "CANDLE_UPDATE"
    CANDLE_CLOSE = "CANDLE_CLOSE"
    SYSTEM_CONNECTION = "SYSTEM_CONNECTION"
    SYSTEM_GAP_RECOVERY = "SYSTEM_GAP_RECOVERY"


class ConnectionState(StrEnum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    RECOVERED = "RECOVERED"
    DEGRADED = "DEGRADED"


@dataclass(slots=True)
class NormalizedEvent:
    event_id: str
    dedupe_key: str
    symbol: str
    timeframe: str | None
    event_type: EventType
    event_time: datetime
    sequence_no: int | None
    received_at: datetime
    source: str
    payload: dict[str, object]
    trace_id: str


@dataclass(slots=True)
class CandleState:
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    candle_start: datetime
    is_closed: bool = False
    last_update: datetime | None = None


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    latest_price: float | None
    candles: dict[str, CandleState]
    volume_24h: float | None
    snapshot_time: datetime
    is_stale: bool = False
    connection_state: ConnectionState = ConnectionState.CONNECTED
