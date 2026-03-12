from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import TypeVar

from ...domain.seed_data import default_seed_data
from ...domain.entities.session import (
    BacktestRun,
    BacktestTrade,
    LogEntry,
    Order,
    Position,
    RiskEvent,
    Session,
    SessionStatus,
    Signal,
)
from ...domain.entities.strategy import Strategy, StrategyVersion
from .lab_store import LabStore


def _now() -> datetime:
    return datetime.now(UTC)


T = TypeVar("T")


class InMemoryLabStore(LabStore):
    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}
        self._versions: dict[str, StrategyVersion] = {}
        self._sessions: dict[str, Session] = {}
        self._signals: dict[str, Signal] = {}
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, Order] = {}
        self._backtest_runs: dict[str, BacktestRun] = {}
        self._backtest_trades: dict[str, BacktestTrade] = {}
        self._risk_events: dict[str, RiskEvent] = {}
        self._logs: list[LogEntry] = []
        self._universe: list[dict[str, object]] = []

    def seed_defaults(self) -> None:
        if self._strategies:
            return
        seed_data = default_seed_data(_now())
        for bundle in seed_data.strategy_bundles:
            strategy = replace(bundle.strategy, latest_version_id=None, latest_version_no=None)
            self.create_strategy(strategy)
            self.create_strategy_version(bundle.version)
            strategy.latest_version_id = bundle.version.id
            strategy.latest_version_no = bundle.version.version_no
            self.update_strategy(strategy)
        self._universe = [dict(item) for item in seed_data.universe_symbols]
        for log in seed_data.logs:
            self.append_log(log)

    def create_strategy(self, strategy: Strategy) -> Strategy:
        self._strategies[strategy.id] = strategy
        return strategy

    def get_strategy_by_id(self, strategy_id: str) -> Strategy | None:
        return self._strategies.get(strategy_id)

    def list_strategies(self) -> list[Strategy]:
        rows = list(self._strategies.values())
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows

    def update_strategy(self, strategy: Strategy) -> Strategy:
        self._strategies[strategy.id] = strategy
        return strategy

    def create_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        self._versions[version.id] = version
        return version

    def update_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        self._versions[version.id] = version
        return version

    def get_strategy_version_by_id(self, version_id: str) -> StrategyVersion | None:
        return self._versions.get(version_id)

    def list_strategy_versions_by_ids(self, version_ids: list[str]) -> list[StrategyVersion]:
        if not version_ids:
            return []
        wanted = set(version_ids)
        return [item for item in self._versions.values() if item.id in wanted]

    def list_strategy_versions(self, strategy_id: str) -> list[StrategyVersion]:
        rows = [item for item in self._versions.values() if item.strategy_id == strategy_id]
        rows.sort(key=lambda item: item.version_no)
        return rows

    def create_session(self, session: Session) -> Session:
        self._sessions[session.id] = session
        return session

    def update_session(self, session: Session) -> Session:
        self._sessions[session.id] = session
        return session

    def get_session_by_id(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[Session]:
        rows = list(self._sessions.values())
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows

    def update_session_status(self, session_id: str, status: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.status = SessionStatus(status)
        session.updated_at = _now()
        if status in {SessionStatus.STOPPED.value, SessionStatus.FAILED.value}:
            session.ended_at = _now()
        return session

    def create_signal(self, signal: Signal) -> Signal:
        self._signals[signal.id] = signal
        return signal

    def list_signals_by_session(self, session_id: str) -> list[Signal]:
        return [item for item in self._signals.values() if item.session_id == session_id]

    def list_signals_for_sessions(self, session_ids: list[str]) -> list[Signal]:
        if not session_ids:
            return []
        wanted = set(session_ids)
        rows = [item for item in self._signals.values() if item.session_id in wanted]
        rows.sort(key=lambda item: item.snapshot_time, reverse=True)
        return rows

    def create_position(self, position: Position) -> Position:
        self._positions[position.id] = position
        return position

    def get_position_by_id(self, position_id: str) -> Position | None:
        return self._positions.get(position_id)

    def list_positions_by_session(self, session_id: str) -> list[Position]:
        return [item for item in self._positions.values() if item.session_id == session_id]

    def list_positions_for_sessions(self, session_ids: list[str]) -> list[Position]:
        if not session_ids:
            return []
        wanted = set(session_ids)
        rows = [item for item in self._positions.values() if item.session_id in wanted]
        rows.sort(key=lambda item: item.entry_time or datetime.min.replace(tzinfo=UTC), reverse=True)
        return rows

    def update_position(self, position: Position) -> Position:
        self._positions[position.id] = position
        return position

    def create_order(self, order: Order) -> Order:
        self._orders[order.id] = order
        return order

    def list_orders_by_session(self, session_id: str) -> list[Order]:
        return [item for item in self._orders.values() if item.session_id == session_id]

    def create_backtest_run(self, run: BacktestRun) -> BacktestRun:
        self._backtest_runs[run.id] = run
        return run

    def get_backtest_run_by_id(self, run_id: str) -> BacktestRun | None:
        return self._backtest_runs.get(run_id)

    def list_backtest_runs(self) -> list[BacktestRun]:
        rows = list(self._backtest_runs.values())
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows

    def update_backtest_run(self, run: BacktestRun) -> BacktestRun:
        self._backtest_runs[run.id] = run
        return run

    def create_backtest_trades_bulk(self, trades: list[BacktestTrade]) -> list[BacktestTrade]:
        for trade in trades:
            self._backtest_trades[trade.id] = trade
        return trades

    def list_backtest_trades_by_run(self, run_id: str) -> list[BacktestTrade]:
        return [item for item in self._backtest_trades.values() if item.backtest_run_id == run_id]

    def create_risk_event(self, event: RiskEvent) -> RiskEvent:
        self._risk_events[event.id] = event
        return event

    def list_risk_events_by_session(self, session_id: str) -> list[RiskEvent]:
        return [item for item in self._risk_events.values() if item.session_id == session_id]

    def list_risk_events_for_sessions(self, session_ids: list[str]) -> list[RiskEvent]:
        if not session_ids:
            return []
        wanted = set(session_ids)
        rows = [item for item in self._risk_events.values() if item.session_id in wanted]
        rows.sort(key=lambda item: item.created_at, reverse=True)
        return rows

    def append_log(self, entry: LogEntry) -> LogEntry:
        self._logs.append(entry)
        return entry

    def query_logs(
        self,
        channel: str,
        session_id: str | None = None,
        strategy_version_id: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        rows = [item for item in self._logs if item.channel == channel]
        if session_id is not None:
            rows = [item for item in rows if item.session_id == session_id]
        if strategy_version_id is not None:
            rows = [item for item in rows if item.strategy_version_id == strategy_version_id]
        if symbol is not None:
            rows = [item for item in rows if item.symbol == symbol]
        rows.sort(key=lambda item: item.logged_at, reverse=True)
        return rows[:limit]

    def get_current_universe(self) -> list[dict[str, object]]:
        return [dict(item) for item in self._universe]

    def update_universe(self, symbols: list[str]) -> list[dict[str, object]]:
        self._universe = [
            {
                "symbol": symbol,
                "turnover_24h_krw": None,
                "surge_score": None,
                "selected": True,
            }
            for symbol in symbols
        ]
        return self.get_current_universe()

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        return self.get_strategy_by_id(strategy_id)

    def get_strategy_version(self, version_id: str) -> StrategyVersion | None:
        return self.get_strategy_version_by_id(version_id)

    def get_session(self, session_id: str) -> Session | None:
        return self.get_session_by_id(session_id)

    def list_session_signals(self, session_id: str) -> list[Signal]:
        return self.list_signals_by_session(session_id)

    def list_session_positions(self, session_id: str) -> list[Position]:
        return self.list_positions_by_session(session_id)

    def list_session_orders(self, session_id: str) -> list[Order]:
        return self.list_orders_by_session(session_id)

    def list_session_risk_events(self, session_id: str) -> list[RiskEvent]:
        return self.list_risk_events_by_session(session_id)

    def get_backtest_run(self, run_id: str) -> BacktestRun | None:
        return self.get_backtest_run_by_id(run_id)

    def list_backtest_trades(self, run_id: str) -> list[BacktestTrade]:
        return self.list_backtest_trades_by_run(run_id)
