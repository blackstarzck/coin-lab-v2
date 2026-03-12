from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class StrategyType(StrEnum):
    DSL = "dsl"
    PLUGIN = "plugin"
    HYBRID = "hybrid"


@dataclass(slots=True)
class Strategy:
    id: str
    strategy_key: str
    name: str
    strategy_type: StrategyType
    description: str | None
    is_active: bool
    latest_version_id: str | None
    latest_version_no: int | None
    labels: list[str] = field(default_factory=list)
    last_7d_return_pct: float | None = None
    last_7d_win_rate: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class StrategyVersion:
    id: str
    strategy_id: str
    version_no: int
    schema_version: str
    config_json: dict[str, object]
    config_hash: str
    labels: list[str] = field(default_factory=list)
    notes: str | None = None
    is_validated: bool = False
    validation_summary: dict[str, object] | None = None
    created_by: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
