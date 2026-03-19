from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, TypeVar

from app.domain.entities.market import CandleState, MarketSnapshot
from app.domain.strategy_runtime import DetectorResult, ExplainItem, MarketStructure


@dataclass(slots=True, frozen=True, kw_only=True)
class DetectorContext:
    snapshot: MarketSnapshot
    symbol: str
    timeframe: str
    config: dict[str, object]


TStructure = TypeVar("TStructure", bound=MarketStructure)


class StructureDetector(Protocol[TStructure]):
    detector_id: str

    def required_history(self, config: dict[str, object]) -> int:
        ...

    def evaluate(self, context: DetectorContext) -> DetectorResult[TStructure]:
        ...


def resolve_candles(snapshot: MarketSnapshot, timeframe: str) -> list[CandleState]:
    history = list(snapshot.candle_history.get(timeframe, ()))
    current = snapshot.candles.get(timeframe)
    if current is None:
        return history
    if history and history[-1].candle_start == current.candle_start:
        history[-1] = current
    else:
        history.append(current)
    return history


def build_structure_id(
    detector_id: str,
    *,
    symbol: str,
    timeframe: str,
    formed_at: datetime | None,
    direction: str | None = None,
) -> str:
    formed_at_token = formed_at.isoformat() if formed_at is not None else "na"
    direction_token = direction or "na"
    return f"{detector_id}:{symbol}:{timeframe}:{formed_at_token}:{direction_token}"


def timeframe_missing_result(
    detector_id: str,
    *,
    parameters: tuple[ExplainItem, ...] = (),
) -> DetectorResult[TStructure]:
    return DetectorResult(
        detector_id=detector_id,
        ready=False,
        matched=False,
        reason_codes=("DETECTOR_TIMEFRAME_MISSING",),
        parameters=parameters,
    )


def history_not_ready_result(
    detector_id: str,
    *,
    facts: tuple[ExplainItem, ...] = (),
    parameters: tuple[ExplainItem, ...] = (),
) -> DetectorResult[TStructure]:
    return DetectorResult(
        detector_id=detector_id,
        ready=False,
        matched=False,
        reason_codes=("DETECTOR_HISTORY_NOT_READY",),
        facts=facts,
        parameters=parameters,
    )
