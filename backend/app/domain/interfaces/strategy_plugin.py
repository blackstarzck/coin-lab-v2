from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from app.domain.entities.strategy_decision import StrategyDecision


@dataclass(frozen=True, slots=True)
class StrategyPluginFieldOption:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class StrategyPluginFieldDefinition:
    key: str
    label: str
    kind: str
    helper_text: str
    step: float | None = None
    display: str | None = None
    options: tuple[StrategyPluginFieldOption, ...] = field(default_factory=tuple)
    summary: bool = False


@dataclass(frozen=True, slots=True)
class StrategyPluginMetadata:
    plugin_id: str
    label: str
    version: str
    description: str
    default_config: dict[str, str | int | float | bool]
    fields: tuple[StrategyPluginFieldDefinition, ...] = field(default_factory=tuple)


class StrategyPlugin(ABC):
    plugin_id: str
    plugin_version: str

    @abstractmethod
    def metadata(self) -> StrategyPluginMetadata:
        """Describe plugin metadata for UI and configuration workflows."""
        ...

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
