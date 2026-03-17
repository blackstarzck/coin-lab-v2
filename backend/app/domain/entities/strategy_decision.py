from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

ExplainScalar = float | int | bool | str | None
ExplainItem = dict[str, ExplainScalar]


class PluginAction(StrEnum):
    HOLD = "HOLD"
    ENTER = "ENTER"
    EXIT = "EXIT"


@dataclass(slots=True)
class StrategyDecision:
    action: PluginAction
    confidence: float | None = None
    signal_price: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    matched_conditions: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    facts: list[ExplainItem] = field(default_factory=list)
    parameters: list[ExplainItem] = field(default_factory=list)
