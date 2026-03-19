from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.domain.entities.market import MarketSnapshot
from app.domain.strategy_runtime import StrategyDecisionDraft


@dataclass(slots=True, frozen=True, kw_only=True)
class ComposerContext:
    snapshot: MarketSnapshot
    symbol: str
    timeframe: str
    config: dict[str, object]
    strategy_config: dict[str, object] | None = None


class StrategyComposer(Protocol):
    composer_id: str

    def validate(self, config: dict[str, object]) -> None:
        ...

    def compose(self, context: ComposerContext) -> StrategyDecisionDraft:
        ...
