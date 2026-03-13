from __future__ import annotations

from pydantic import BaseModel


class UniverseSymbolResponse(BaseModel):
    symbol: str
    turnover_24h_krw: float
    surge_score: float
    selected: bool
    active_compare_session_count: int
    has_open_position: bool
    has_recent_signal: bool
    risk_blocked: bool


class UniverseCatalogItemResponse(BaseModel):
    symbol: str
    korean_name: str
    english_name: str
    market_warning: str | None = None
    turnover_24h_krw: float
    trade_price: float | None = None


class UniversePreviewRequest(BaseModel):
    symbol_scope: dict[str, object]


class UniversePreviewResponse(BaseModel):
    symbols: list[str]
    count: int
