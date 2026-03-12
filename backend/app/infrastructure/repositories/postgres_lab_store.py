from __future__ import annotations

from app.domain.entities.session import BacktestRun, BacktestTrade, LogEntry, Order, Position, RiskEvent, Session, Signal
from app.domain.entities.strategy import Strategy, StrategyVersion
from app.domain.value_objects.pagination import PaginationParams
from app.infrastructure.repositories.lab_store import LabStore


class PostgresLabStore(LabStore):
    def _raise(self) -> None:
        raise NotImplementedError("Configure Supabase/Postgres to use COIN_LAB_STORE_BACKEND=postgres")

    def create_strategy(self, strategy: Strategy) -> Strategy:
        self._raise()

    def get_strategy_by_id(self, strategy_id: str) -> Strategy | None:
        self._raise()

    def list_strategies(self, pagination: PaginationParams, is_active: bool | None = None, label: str | None = None) -> tuple[list[Strategy], int]:
        self._raise()

    def update_strategy(self, strategy: Strategy) -> Strategy:
        self._raise()

    def create_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        self._raise()

    def get_strategy_version_by_id(self, version_id: str) -> StrategyVersion | None:
        self._raise()

    def list_strategy_versions(self, strategy_id: str) -> list[StrategyVersion]:
        self._raise()

    def create_session(self, session: Session) -> Session:
        self._raise()

    def get_session_by_id(self, session_id: str) -> Session | None:
        self._raise()

    def list_sessions(self, pagination: PaginationParams) -> tuple[list[Session], int]:
        self._raise()

    def update_session_status(self, session_id: str, status: str) -> Session | None:
        self._raise()

    def create_signal(self, signal: Signal) -> Signal:
        self._raise()

    def list_signals_by_session(self, session_id: str) -> list[Signal]:
        self._raise()

    def create_position(self, position: Position) -> Position:
        self._raise()

    def get_position_by_id(self, position_id: str) -> Position | None:
        self._raise()

    def list_positions_by_session(self, session_id: str) -> list[Position]:
        self._raise()

    def update_position(self, position: Position) -> Position:
        self._raise()

    def create_order(self, order: Order) -> Order:
        self._raise()

    def list_orders_by_session(self, session_id: str) -> list[Order]:
        self._raise()

    def create_backtest_run(self, run: BacktestRun) -> BacktestRun:
        self._raise()

    def get_backtest_run_by_id(self, run_id: str) -> BacktestRun | None:
        self._raise()

    def list_backtest_runs(self, pagination: PaginationParams) -> tuple[list[BacktestRun], int]:
        self._raise()

    def update_backtest_run(self, run: BacktestRun) -> BacktestRun:
        self._raise()

    def create_backtest_trades_bulk(self, trades: list[BacktestTrade]) -> list[BacktestTrade]:
        self._raise()

    def list_backtest_trades_by_run(self, run_id: str) -> list[BacktestTrade]:
        self._raise()

    def create_risk_event(self, event: RiskEvent) -> RiskEvent:
        self._raise()

    def list_risk_events_by_session(self, session_id: str) -> list[RiskEvent]:
        self._raise()

    def append_log(self, entry: LogEntry) -> LogEntry:
        self._raise()

    def query_logs(self, channel: str, session_id: str | None = None, strategy_version_id: str | None = None, symbol: str | None = None, limit: int = 100) -> list[LogEntry]:
        self._raise()

    def get_current_universe(self) -> list[dict[str, object]]:
        self._raise()

    def update_universe(self, symbols: list[dict[str, object]]) -> list[dict[str, object]]:
        self._raise()
