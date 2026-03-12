from __future__ import annotations

from abc import ABC, abstractmethod

from ...domain.entities.session import BacktestRun, BacktestTrade, LogEntry, Order, Position, RiskEvent, Session, Signal
from ...domain.entities.strategy import Strategy, StrategyVersion


class LabStore(ABC):
    @abstractmethod
    def seed_defaults(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_strategies(self) -> list[Strategy]:
        raise NotImplementedError

    @abstractmethod
    def get_strategy(self, strategy_id: str) -> Strategy | None:
        raise NotImplementedError

    @abstractmethod
    def create_strategy(self, strategy: Strategy) -> Strategy:
        raise NotImplementedError

    @abstractmethod
    def update_strategy(self, strategy: Strategy) -> Strategy:
        raise NotImplementedError

    @abstractmethod
    def list_strategy_versions(self, strategy_id: str) -> list[StrategyVersion]:
        raise NotImplementedError

    @abstractmethod
    def get_strategy_version(self, version_id: str) -> StrategyVersion | None:
        raise NotImplementedError

    @abstractmethod
    def list_strategy_versions_by_ids(self, version_ids: list[str]) -> list[StrategyVersion]:
        raise NotImplementedError

    @abstractmethod
    def create_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        raise NotImplementedError

    @abstractmethod
    def update_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        raise NotImplementedError

    @abstractmethod
    def create_session(self, session: Session) -> Session:
        raise NotImplementedError

    @abstractmethod
    def update_session(self, session: Session) -> Session:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self) -> list[Session]:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, session_id: str) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    def update_session_status(self, session_id: str, status: str) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    def list_session_signals(self, session_id: str) -> list[Signal]:
        raise NotImplementedError

    @abstractmethod
    def list_signals_for_sessions(self, session_ids: list[str]) -> list[Signal]:
        raise NotImplementedError

    @abstractmethod
    def create_signal(self, signal: Signal) -> Signal:
        raise NotImplementedError

    @abstractmethod
    def list_session_positions(self, session_id: str) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def list_positions_for_sessions(self, session_ids: list[str]) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def create_position(self, position: Position) -> Position:
        raise NotImplementedError

    @abstractmethod
    def update_position(self, position: Position) -> Position:
        raise NotImplementedError

    @abstractmethod
    def list_session_orders(self, session_id: str) -> list[Order]:
        raise NotImplementedError

    @abstractmethod
    def create_order(self, order: Order) -> Order:
        raise NotImplementedError

    @abstractmethod
    def list_session_risk_events(self, session_id: str) -> list[RiskEvent]:
        raise NotImplementedError

    @abstractmethod
    def list_risk_events_for_sessions(self, session_ids: list[str]) -> list[RiskEvent]:
        raise NotImplementedError

    @abstractmethod
    def create_risk_event(self, event: RiskEvent) -> RiskEvent:
        raise NotImplementedError

    @abstractmethod
    def list_backtest_runs(self) -> list[BacktestRun]:
        raise NotImplementedError

    @abstractmethod
    def get_backtest_run(self, run_id: str) -> BacktestRun | None:
        raise NotImplementedError

    @abstractmethod
    def create_backtest_run(self, run: BacktestRun) -> BacktestRun:
        raise NotImplementedError

    @abstractmethod
    def update_backtest_run(self, run: BacktestRun) -> BacktestRun:
        raise NotImplementedError

    @abstractmethod
    def list_backtest_trades(self, run_id: str) -> list[BacktestTrade]:
        raise NotImplementedError

    @abstractmethod
    def get_current_universe(self) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def update_universe(self, symbols: list[str]) -> list[dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def append_log(self, entry: LogEntry) -> LogEntry:
        raise NotImplementedError

    @abstractmethod
    def query_logs(
        self,
        channel: str,
        session_id: str | None = None,
        strategy_version_id: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        raise NotImplementedError
