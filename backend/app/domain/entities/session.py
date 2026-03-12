from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class ExecutionMode(StrEnum):
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class SessionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class PositionState(StrEnum):
    NONE = "NONE"
    OPENING = "OPENING"
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"


class OrderState(StrEnum):
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class SignalAction(StrEnum):
    ENTER = "ENTER"
    EXIT = "EXIT"


class SignalState(StrEnum):
    GENERATED = "GENERATED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CONSUMED = "CONSUMED"


class RiskState(StrEnum):
    CLEAR = "CLEAR"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"
    KILL_SWITCHED = "KILL_SWITCHED"


class ReentryState(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    COOLDOWN = "COOLDOWN"
    WAIT_RESET = "WAIT_RESET"
    DISABLED = "DISABLED"


class OrderRole(StrEnum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class ExitReason(StrEnum):
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP = "TRAILING_STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    TIME_STOP = "TIME_STOP"
    MANUAL_STOP = "MANUAL_STOP"
    EMERGENCY_KILL = "EMERGENCY_KILL"
    EXCHANGE_REJECT = "EXCHANGE_REJECT"
    STRATEGY_EXIT = "STRATEGY_EXIT"
    STOP_LOSS_INTRA_BAR_CONSERVATIVE = "STOP_LOSS_INTRA_BAR_CONSERVATIVE"


@dataclass(slots=True)
class Session:
    id: str
    mode: ExecutionMode
    status: SessionStatus
    strategy_version_id: str
    symbol_scope_json: dict[str, object]
    risk_overrides_json: dict[str, object]
    config_snapshot: dict[str, object]
    performance_json: dict[str, object]
    health_json: dict[str, object]
    trace_id: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class Signal:
    id: str
    session_id: str
    strategy_version_id: str
    symbol: str
    timeframe: str
    action: str
    signal_price: float | None
    confidence: float | None
    reason_codes: list[str]
    snapshot_time: datetime
    blocked: bool


@dataclass(slots=True)
class Position:
    id: str
    session_id: str
    strategy_version_id: str
    symbol: str
    position_state: PositionState
    side: str
    entry_time: datetime | None
    avg_entry_price: float | None
    quantity: float
    stop_loss_price: float | None
    take_profit_price: float | None
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass(slots=True)
class Order:
    id: str
    session_id: str
    strategy_version_id: str
    symbol: str
    order_role: str
    order_type: str
    order_state: OrderState
    requested_price: float | None
    executed_price: float | None
    requested_qty: float
    executed_qty: float
    retry_count: int
    submitted_at: datetime | None
    filled_at: datetime | None


@dataclass(slots=True)
class RiskEvent:
    id: str
    session_id: str
    strategy_version_id: str
    severity: str
    code: str
    symbol: str | None
    message: str
    payload_preview: dict[str, object]
    created_at: datetime


@dataclass(slots=True)
class BacktestRun:
    id: str
    status: str
    strategy_version_id: str
    symbols: list[str]
    timeframes: list[str]
    date_from: datetime
    date_to: datetime
    initial_capital: float
    metrics: dict[str, object]
    created_at: datetime
    completed_at: datetime | None


@dataclass(slots=True)
class BacktestTrade:
    id: str
    backtest_run_id: str
    symbol: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    qty: float
    pnl: float
    pnl_pct: float
    fee_amount: float
    slippage_amount: float
    exit_reason: str


@dataclass(slots=True)
class LogEntry:
    id: str
    channel: str
    level: str
    session_id: str | None
    strategy_version_id: str | None
    symbol: str | None
    event_type: str
    message: str
    payload: dict[str, object]
    logged_at: datetime


@dataclass(slots=True)
class FillResult:
    filled: bool
    fill_price: float | None
    fill_qty: float
    fee_amount: float
    slippage_amount: float
    exit_reason: str | None = None


@dataclass(slots=True)
class OrderIntent:
    signal_id: str
    session_id: str
    symbol: str
    side: str
    order_type: str
    order_role: str
    requested_qty: float
    limit_price: float | None = None
    timeout_sec: float = 15.0
    fallback_to_market: bool = True
    idempotency_key: str = ""
    trace_id: str = ""


@dataclass(slots=True)
class RiskCheckResult:
    passed: bool
    risk_state: str
    blocked_codes: list[str]
    warnings: list[str]
