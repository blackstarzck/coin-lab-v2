from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StatusBar(BaseModel):
    running_session_count: int
    paper_session_count: int
    live_session_count: int
    failed_session_count: int
    degraded_session_count: int
    active_symbol_count: int


class StrategyCard(BaseModel):
    strategy_id: str
    strategy_key: str
    strategy_name: str
    strategy_type: Literal["dsl", "plugin", "hybrid"]
    latest_version_id: str | None = None
    latest_version_no: int | None = None
    is_active: bool
    is_validated: bool
    active_session_count: int
    last_7d_return_pct: float | None = None
    last_signal_at: datetime | None = None


class UniverseSymbolSummary(BaseModel):
    symbol: str
    turnover_24h_krw: float
    surge_score: float
    selected: bool
    active_compare_session_count: int
    has_open_position: bool
    has_recent_signal: bool
    risk_blocked: bool


class UniverseSummary(BaseModel):
    active_symbol_count: int
    watchlist_symbol_count: int
    with_open_position_count: int
    with_recent_signal_count: int
    symbols: list[UniverseSymbolSummary] = Field(default_factory=list)


class RiskOverviewItem(BaseModel):
    session_id: str
    severity: str
    code: str
    message: str
    created_at: datetime


class RiskOverview(BaseModel):
    active_alert_count: int
    blocked_signal_count_1h: int
    daily_loss_limit_session_count: int
    max_drawdown_session_count: int
    items: list[RiskOverviewItem] = Field(default_factory=list)


class RecentSignal(BaseModel):
    id: str
    session_id: str
    strategy_version_id: str
    symbol: str
    action: str
    signal_price: float | None = None
    confidence: float | None = None
    blocked: bool
    reason_codes: list[str] = Field(default_factory=list)
    snapshot_time: datetime


class MonitoringSummaryResponse(BaseModel):
    status_bar: StatusBar
    strategy_cards: list[StrategyCard] = Field(default_factory=list)
    universe_summary: UniverseSummary
    risk_overview: RiskOverview
    recent_signals: list[RecentSignal] = Field(default_factory=list)
