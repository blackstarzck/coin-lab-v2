from __future__ import annotations

from dataclasses import dataclass

from .market_structures import ExplainItem, MarketStructure


@dataclass(slots=True, kw_only=True)
class SetupConfluence:
    score: int
    max_score: int
    matched_conditions: tuple[str, ...]
    failed_conditions: tuple[str, ...]
    facts: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True)
class RiskEnvelope:
    invalidation_price: float | None
    stop_loss_price: float | None
    take_profit_prices: tuple[float, ...]
    trailing_activation_price: float | None
    max_holding_bars: int | None


@dataclass(slots=True, kw_only=True)
class EntrySetup:
    setup_id: str
    symbol: str
    timeframe: str
    direction: str
    setup_type: str
    valid: bool
    confidence: float | None
    trigger_price: float | None
    preferred_entry_zone: tuple[float, float] | None
    invalidation_price: float | None
    confluence: SetupConfluence
    risk: RiskEnvelope
    structures: tuple[MarketStructure, ...]
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True)
class ExitSetup:
    setup_id: str
    symbol: str
    timeframe: str
    exit_type: str
    valid: bool
    priority: int
    trigger_price: float | None
    invalidation_price: float | None
    structures: tuple[MarketStructure, ...]
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True)
class StrategyDecisionDraft:
    action: str
    confidence: float | None
    entry_setup: EntrySetup | None
    exit_setup: ExitSetup | None
    matched_conditions: tuple[str, ...] = ()
    failed_conditions: tuple[str, ...] = ()
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
