from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    mode: Literal["BACKTEST", "PAPER", "LIVE"]
    strategy_version_id: str
    symbol_scope: dict[str, object]
    risk_overrides: dict[str, object] = Field(default_factory=dict)
    confirm_live: bool = False
    acknowledge_risk: bool = False


class SessionResponse(BaseModel):
    id: str
    strategy_version_id: str
    mode: Literal["BACKTEST", "PAPER", "LIVE"]
    status: Literal["PENDING", "RUNNING", "STOPPING", "STOPPED", "FAILED"]
    symbol_scope: dict[str, object]
    started_at: datetime | None = None
    ended_at: datetime | None = None
    performance: dict[str, object] | None = None
    health: dict[str, object] | None = None


class SessionStopRequest(BaseModel):
    reason: str


class SessionKillRequest(BaseModel):
    reason: str
    close_open_positions: bool = True


class SessionStopResponse(BaseModel):
    session_id: str
    previous_status: Literal["PENDING", "RUNNING", "STOPPING", "STOPPED", "FAILED"]
    current_status: Literal["PENDING", "RUNNING", "STOPPING", "STOPPED", "FAILED"]
    reason: str


class SignalResponse(BaseModel):
    id: str
    strategy_version_id: str
    symbol: str
    timeframe: str
    action: str
    signal_price: float | None = None
    confidence: float | None = None
    reason_codes: list[str]
    snapshot_time: datetime
    blocked: bool


class PositionResponse(BaseModel):
    id: str
    strategy_version_id: str
    symbol: str
    position_state: Literal["NONE", "OPENING", "OPEN", "CLOSING", "CLOSED", "FAILED"]
    side: str
    entry_time: datetime | None = None
    avg_entry_price: float | None = None
    quantity: float
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    unrealized_pnl: float
    unrealized_pnl_pct: float


class OrderResponse(BaseModel):
    id: str
    session_id: str
    strategy_version_id: str
    symbol: str
    order_role: str
    order_type: str
    order_state: Literal["CREATED", "SUBMITTED", "PARTIALLY_FILLED", "FILLED", "CANCELLED", "REJECTED", "EXPIRED", "FAILED"]
    requested_price: float | None = None
    executed_price: float | None = None
    requested_qty: float
    executed_qty: float
    retry_count: int
    submitted_at: datetime | None = None
    filled_at: datetime | None = None


class RiskEventResponse(BaseModel):
    id: str
    session_id: str
    strategy_version_id: str
    severity: str
    code: str
    symbol: str | None = None
    message: str
    payload_preview: dict[str, object]
    created_at: datetime


class PerformanceResponse(BaseModel):
    realized_pnl: float
    realized_pnl_pct: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    trade_count: int
    win_rate_pct: float
    max_drawdown_pct: float


class SessionCreateRequest(SessionCreate):
    pass

class SessionTransitionResponse(SessionStopResponse):
    pass
