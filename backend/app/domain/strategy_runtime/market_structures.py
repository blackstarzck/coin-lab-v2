from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeAlias, TypeVar

ExplainScalar: TypeAlias = float | int | bool | str | None


@dataclass(slots=True, frozen=True, kw_only=True)
class ExplainItem:
    label: str
    value: ExplainScalar

    def as_dict(self) -> dict[str, ExplainScalar]:
        return {"label": self.label, "value": self.value}


def serialize_explain_items(items: Iterable[ExplainItem]) -> list[dict[str, ExplainScalar]]:
    return [item.as_dict() for item in items]


T = TypeVar("T")


@dataclass(slots=True, kw_only=True)
class DetectorResult(Generic[T]):
    detector_id: str
    ready: bool
    matched: bool
    items: tuple[T, ...] = ()
    primary: T | None = None
    reason_codes: tuple[str, ...] = ()
    facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()

    def __post_init__(self) -> None:
        if not self.ready and self.matched:
            raise ValueError("matched cannot be true when ready is false")
        if self.primary is not None and self.primary not in self.items:
            raise ValueError("primary must be one of the detector result items")


@dataclass(slots=True, kw_only=True)
class MarketStructure:
    structure_id: str
    kind: str
    symbol: str
    timeframe: str
    direction: str | None
    formed_at: datetime | None
    invalidated_at: datetime | None
    confidence: float | None
    facts: tuple[ExplainItem, ...] = ()
    reason_codes: tuple[str, ...] = ()


@dataclass(slots=True, kw_only=True)
class TrendContext(MarketStructure):
    support: float | None
    resistance: float | None
    average_close: float | None
    start_close: float | None
    latest_close: float | None
    trend_state: str


@dataclass(slots=True, kw_only=True)
class PriceZone(MarketStructure):
    lower: float
    upper: float
    midpoint: float
    invalidation_price: float | None
    retested: bool
    active: bool


@dataclass(slots=True, kw_only=True)
class OrderBlockZone(PriceZone):
    source_candle_at: datetime | None
    impulse_candle_at: datetime | None
    body_ratio: float | None
    displacement_pct: float | None


@dataclass(slots=True, kw_only=True)
class FairValueGapZone(PriceZone):
    left_candle_at: datetime | None
    middle_candle_at: datetime | None
    right_candle_at: datetime | None
    gap_pct: float | None


@dataclass(slots=True, kw_only=True)
class SupportResistanceZone(PriceZone):
    touch_count: int
    source: str


@dataclass(slots=True, kw_only=True)
class StructureBreak(MarketStructure):
    break_type: str
    reference_price: float | None
    break_price: float | None
    confirmed: bool


@dataclass(slots=True, kw_only=True)
class RetestEvaluation(MarketStructure):
    zone_kind: str
    zone_lower: float | None
    zone_upper: float | None
    retest_price: float | None
    accepted: bool
    rejection_confirmed: bool
