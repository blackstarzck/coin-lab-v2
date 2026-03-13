from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BacktestRunRequest(BaseModel):
    strategy_version_id: str
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(min_length=1)
    date_from: datetime
    date_to: datetime
    execution_overrides: dict[str, object] = Field(default_factory=dict)


class BacktestRunResponse(BaseModel):
    run_id: str
    status: str
    strategy_version_id: str
    symbols: list[str]
    date_from: datetime
    date_to: datetime
    queued_at: datetime


class BacktestDetailResponse(BaseModel):
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


class BacktestTradeResponse(BaseModel):
    id: str
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


class BacktestPerformanceResponse(BaseModel):
    total_return_pct: float
    max_drawdown_pct: float
    win_rate_pct: float
    profit_factor: float
    trade_count: int
    avg_hold_minutes: float
    sharpe_ratio: float


class EquityCurvePointResponse(BaseModel):
    time: datetime
    equity: float
    drawdown_pct: float


class BacktestCompareRequest(BaseModel):
    against_run_ids: list[str]


class BacktestListResponse(BaseModel):
    id: str
    status: str
    strategy_version_id: str
    symbols: list[str]
    timeframes: list[str]
    date_from: datetime
    date_to: datetime
    total_return_pct: float | None = None
    trade_count: int | None = None
    created_at: datetime
    completed_at: datetime | None
