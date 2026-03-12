from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


class StrategyPlugin(ABC):
    plugin_id: str
    plugin_version: str

    @abstractmethod
    def validate(self, config: dict[str, object]) -> None:
        """Raise if plugin-specific config is invalid."""
        ...

    @abstractmethod
    def evaluate(self, snapshot: Any) -> Any:
        """Evaluate strategy against a market snapshot. Returns StrategyDecision."""
        ...

    @abstractmethod
    def explain(self, snapshot: Any) -> dict[str, object]:
        """Generate explain/debug payload for the given snapshot."""
        ...
