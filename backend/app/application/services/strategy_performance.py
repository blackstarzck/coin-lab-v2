from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ...domain.entities.session import Session
from ...domain.entities.strategy import StrategyVersion


@dataclass(frozen=True, slots=True)
class StrategyPerformanceSnapshot:
    last_7d_return_pct: float | None
    last_7d_win_rate: float | None
    session_count: int


@dataclass(slots=True)
class _AggregateState:
    session_count: int = 0
    total_initial_capital: float = 0.0
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0
    total_trade_count: int = 0
    total_winning_trade_count: float = 0.0


def build_strategy_performance_map(
    sessions: list[Session],
    versions: list[StrategyVersion],
    *,
    now: datetime | None = None,
    lookback: timedelta = timedelta(days=7),
) -> dict[str, StrategyPerformanceSnapshot]:
    current_time = now or datetime.now(UTC)
    window_start = current_time - lookback
    strategy_ids_by_version_id = {version.id: version.strategy_id for version in versions}
    aggregates: dict[str, _AggregateState] = {}

    for session in sessions:
        if session.updated_at < window_start:
            continue
        strategy_id = strategy_ids_by_version_id.get(session.strategy_version_id)
        if strategy_id is None:
            continue

        aggregate = aggregates.setdefault(strategy_id, _AggregateState())
        aggregate.session_count += 1
        aggregate.total_initial_capital += _as_float(session.performance_json.get("initial_capital"))
        aggregate.total_realized_pnl += _as_float(session.performance_json.get("realized_pnl"))
        aggregate.total_unrealized_pnl += _as_float(session.performance_json.get("unrealized_pnl"))

        trade_count = _as_int(session.performance_json.get("trade_count"))
        aggregate.total_trade_count += trade_count
        aggregate.total_winning_trade_count += _winning_trade_count(session.performance_json, trade_count)

    return {
        strategy_id: StrategyPerformanceSnapshot(
            last_7d_return_pct=(
                ((aggregate.total_realized_pnl + aggregate.total_unrealized_pnl) / aggregate.total_initial_capital) * 100
                if aggregate.total_initial_capital > 0
                else None
            ),
            last_7d_win_rate=(
                (aggregate.total_winning_trade_count / aggregate.total_trade_count) * 100
                if aggregate.total_trade_count > 0
                else None
            ),
            session_count=aggregate.session_count,
        )
        for strategy_id, aggregate in aggregates.items()
    }


def _winning_trade_count(performance_json: dict[str, object], trade_count: int) -> float:
    winning_trade_count = performance_json.get("winning_trade_count")
    if winning_trade_count is not None:
        return float(_as_int(winning_trade_count))
    win_rate_pct = _as_float(performance_json.get("win_rate_pct"))
    if trade_count <= 0 or win_rate_pct <= 0:
        return 0.0
    return (win_rate_pct / 100.0) * trade_count


def _as_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0
