from __future__ import annotations

from dataclasses import dataclass

from .market_structures import ExplainItem


@dataclass(slots=True, kw_only=True)
class OrderIntentPlan:
    symbol: str
    side: str
    order_role: str
    order_type: str
    requested_qty: float
    requested_price: float | None
    timeout_sec: float | None
    fallback_to_market: bool
    retries_allowed: int
    reason_codes: tuple[str, ...] = ()
    facts: tuple[ExplainItem, ...] = ()


@dataclass(slots=True, kw_only=True)
class PositionPlan:
    size_mode: str
    notional_krw: float | None
    expected_qty: float
    initial_stop_loss: float | None
    initial_take_profit: float | None
    partial_take_profits: tuple[tuple[float, float], ...] = ()
    trailing_stop_pct: float | None = None


@dataclass(slots=True, kw_only=True)
class ExitPlan:
    exit_type: str
    order_type: str
    trigger_price: float | None
    close_ratio: float
    priority: int
    fallback_to_market: bool
    reason_codes: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True)
class ExecutionEnvelope:
    entry_intent: OrderIntentPlan | None
    position_plan: PositionPlan | None
    exit_plans: tuple[ExitPlan, ...] = ()
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()
