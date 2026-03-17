from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from app.domain.entities.strategy_decision import StrategyDecision


class StrategyPlugin(ABC):
    plugin_id: str
    plugin_version: str

    @abstractmethod
    def validate(self, config: dict[str, object]) -> None:
        """Raise if plugin-specific config is invalid."""
        ...

    @abstractmethod
    def evaluate(self, snapshot: Any, config: dict[str, object] | None = None) -> StrategyDecision:
        """Evaluate strategy against a market snapshot. Returns StrategyDecision."""
        ...

    @abstractmethod
    def explain(self, snapshot: Any, config: dict[str, object] | None = None) -> dict[str, object]:
        """Generate explain/debug payload for the given snapshot."""
        ...
