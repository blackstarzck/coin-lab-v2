from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.session import (
    BacktestRun,
    BacktestTrade,
    ExecutionMode,
    LogEntry,
    Order,
    OrderState,
    Position,
    PositionState,
    RiskEvent,
    Session,
    SessionStatus,
    Signal,
)
from app.domain.entities.strategy import Strategy, StrategyType, StrategyVersion
from app.infrastructure.repositories.lab_store import LabStore

_LOG_TABLE_MAP: dict[str, str] = {
    "system": "system_logs",
    "strategy-execution": "strategy_execution_logs",
    "order-simulation": "order_simulation_logs",
    "risk-control": "risk_control_logs",
    "document-change": "document_change_logs",
}


def _float_or_none(val: object) -> float | None:
    if val is None:
        return None
    return float(str(val))


def _ensure_dict(val: object) -> dict[str, object]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        return json.loads(val)
    return {}


def _ensure_list(val: object) -> list[str]:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return json.loads(val)
    return []


def _row_to_strategy(row: dict[str, Any]) -> Strategy:
    return Strategy(
        id=row["id"],
        strategy_key=row["strategy_key"],
        name=row["name"],
        strategy_type=StrategyType(row["strategy_type"]),
        description=row.get("description"),
        is_active=row["is_active"],
        latest_version_id=row.get("latest_version_id"),
        latest_version_no=row.get("latest_version_no"),
        labels=_ensure_list(row.get("labels_json", [])),
        last_7d_return_pct=_float_or_none(row.get("last_7d_return_pct")),
        last_7d_win_rate=_float_or_none(row.get("last_7d_win_rate")),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_strategy_version(row: dict[str, Any]) -> StrategyVersion:
    return StrategyVersion(
        id=row["id"],
        strategy_id=row["strategy_id"],
        version_no=row["version_no"],
        schema_version=row["schema_version"],
        config_json=_ensure_dict(row["config_json"]),
        config_hash=row["config_hash"],
        labels=_ensure_list(row.get("labels", [])),
        notes=row.get("notes"),
        is_validated=row.get("is_validated", False),
        validation_summary=row.get("validation_summary"),
        created_by=row.get("created_by"),
        created_at=row["created_at"],
    )


def _row_to_session(row: dict[str, Any]) -> Session:
    return Session(
        id=row["id"],
        mode=ExecutionMode(row["mode"]),
        status=SessionStatus(row["status"]),
        strategy_version_id=row["strategy_version_id"],
        symbol_scope_json=_ensure_dict(row.get("symbol_scope_json", {})),
        risk_overrides_json=_ensure_dict(row.get("risk_overrides_json", {})),
        config_snapshot=_ensure_dict(row.get("config_snapshot", {})),
        performance_json=_ensure_dict(row.get("performance_json", {})),
        health_json=_ensure_dict(row.get("health_json", {})),
        trace_id=row["trace_id"],
        started_at=row.get("started_at"),
        ended_at=row.get("ended_at"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_signal(row: dict[str, Any]) -> Signal:
    return Signal(
        id=row["id"],
        session_id=row["session_id"],
        strategy_version_id=row["strategy_version_id"],
        symbol=row["symbol"],
        timeframe=row["timeframe"],
        action=row["signal_action"],
        signal_price=_float_or_none(row.get("signal_price")),
        confidence=_float_or_none(row.get("confidence")),
        reason_codes=_ensure_list(row.get("reason_codes", [])),
        snapshot_time=row["snapshot_time"],
        blocked=row.get("blocked", False),
        explain_payload=row.get("explain_json"),
    )


def _row_to_position(row: dict[str, Any]) -> Position:
    return Position(
        id=row["id"],
        session_id=row["session_id"],
        strategy_version_id=row["strategy_version_id"],
        symbol=row["symbol"],
        position_state=PositionState(row["position_state"]),
        side=row.get("side", "LONG"),
        entry_time=row.get("entry_time"),
        avg_entry_price=_float_or_none(row.get("avg_entry_price")),
        quantity=float(row.get("quantity", 0)),
        stop_loss_price=_float_or_none(row.get("stop_loss_price")),
        take_profit_price=_float_or_none(row.get("take_profit_price")),
        unrealized_pnl=float(row.get("unrealized_pnl", 0)),
        unrealized_pnl_pct=float(row.get("unrealized_pnl_pct", 0)),
    )


def _row_to_order(row: dict[str, Any]) -> Order:
    return Order(
        id=row["id"],
        session_id=row["session_id"],
        strategy_version_id=row["strategy_version_id"],
        symbol=row["symbol"],
        order_role=row["order_role"],
        order_type=row["order_type"],
        order_state=OrderState(row["order_state"]),
        requested_price=_float_or_none(row.get("requested_price")),
        executed_price=_float_or_none(row.get("executed_price")),
        requested_qty=float(row["requested_qty"]),
        executed_qty=float(row.get("executed_qty", 0)),
        retry_count=int(row.get("retry_count", 0)),
        submitted_at=row.get("submitted_at"),
        filled_at=row.get("filled_at"),
    )


def _row_to_backtest_run(row: dict[str, Any]) -> BacktestRun:
    return BacktestRun(
        id=row["id"],
        status=row["status"],
        strategy_version_id=row["strategy_version_id"],
        symbols=_ensure_list(row.get("symbols_json", [])),
        timeframes=_ensure_list(row.get("timeframes_json", [])),
        date_from=row["date_from"],
        date_to=row["date_to"],
        initial_capital=float(row["initial_capital"]),
        metrics=_ensure_dict(row.get("metrics_json") or {}),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


def _row_to_backtest_trade(row: dict[str, Any]) -> BacktestTrade:
    return BacktestTrade(
        id=row["id"],
        backtest_run_id=row["backtest_run_id"],
        symbol=row["symbol"],
        entry_time=row["entry_time"],
        exit_time=row["exit_time"],
        entry_price=float(row["entry_price"]),
        exit_price=float(row["exit_price"]),
        qty=float(row["qty"]),
        pnl=float(row["pnl"]),
        pnl_pct=float(row["pnl_pct"]),
        fee_amount=float(row.get("fee_amount", 0)),
        slippage_amount=float(row.get("slippage_amount", 0)),
        exit_reason=row["exit_reason"],
    )


def _row_to_risk_event(row: dict[str, Any]) -> RiskEvent:
    return RiskEvent(
        id=row["id"],
        session_id=row["session_id"],
        strategy_version_id=row.get("strategy_version_id", ""),
        severity=row["severity"],
        code=row["event_code"],
        symbol=row.get("symbol"),
        message=row.get("message", ""),
        payload_preview=_ensure_dict(row.get("payload_json", {})),
        created_at=row["occurred_at"],
    )


def _row_to_log_entry(row: dict[str, Any], channel: str) -> LogEntry:
    return LogEntry(
        id=str(row["id"]),
        channel=channel,
        level=row["level"],
        trace_id=row.get("trace_id"),
        session_id=row.get("session_id"),
        strategy_version_id=row.get("strategy_version_id"),
        symbol=row.get("symbol"),
        event_type=row["event_type"],
        message=row["message"],
        payload=_ensure_dict(row.get("payload_json") or {}),
        logged_at=row["logged_at"],
    )


class PostgresLabStore(LabStore):
    """LabStore backed by PostgreSQL via psycopg2-binary."""

    def __init__(self, database_url: str, min_conn: int = 2, max_conn: int = 10) -> None:
        import psycopg2.pool

        self._pool: Any = psycopg2.pool.ThreadedConnectionPool(min_conn, max_conn, database_url)

    def _get_conn(self) -> Any:
        return self._pool.getconn()

    def _put_conn(self, conn: Any) -> None:
        try:
            from psycopg2.extensions import TRANSACTION_STATUS_IDLE

            if getattr(conn, "closed", False):
                self._pool.putconn(conn, close=True)
                return

            if conn.get_transaction_status() != TRANSACTION_STATUS_IDLE:
                conn.rollback()

            self._pool.putconn(conn)
        except Exception:
            self._pool.putconn(conn, close=True)

    def _cursor_factory(self) -> Any:
        from psycopg2.extras import RealDictCursor
        return RealDictCursor

    def _json(self, val: object) -> Any:
        from psycopg2.extras import Json
        return Json(val)

    # ── seed ──────────────────────────────────────────────────────────────

    def seed_defaults(self) -> None:
        return None

    # ── strategies ────────────────────────────────────────────────────────

    def create_strategy(self, strategy: Strategy) -> Strategy:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO strategies
                       (id, strategy_key, name, strategy_type, description,
                        is_active, latest_version_id, labels_json,
                        latest_version_no, last_7d_return_pct, last_7d_win_rate,
                        created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        strategy.id, strategy.strategy_key, strategy.name,
                        strategy.strategy_type.value, strategy.description,
                        strategy.is_active, strategy.latest_version_id,
                        self._json(strategy.labels),
                        strategy.latest_version_no,
                        strategy.last_7d_return_pct, strategy.last_7d_win_rate,
                        strategy.created_at, strategy.updated_at,
                    ),
                )
            conn.commit()
            return strategy
        finally:
            self._put_conn(conn)

    def get_strategy(self, strategy_id: str) -> Strategy | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM strategies WHERE id = %s", (strategy_id,))
                row = cur.fetchone()
            return _row_to_strategy(row) if row else None
        finally:
            self._put_conn(conn)

    def list_strategies(self) -> list[Strategy]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM strategies ORDER BY created_at DESC")
                rows = cur.fetchall()
            return [_row_to_strategy(r) for r in rows]
        finally:
            self._put_conn(conn)

    def update_strategy(self, strategy: Strategy) -> Strategy:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE strategies SET
                       strategy_key=%s, name=%s, strategy_type=%s, description=%s,
                       is_active=%s, latest_version_id=%s, labels_json=%s,
                       latest_version_no=%s, last_7d_return_pct=%s,
                       last_7d_win_rate=%s, updated_at=%s
                       WHERE id=%s""",
                    (
                        strategy.strategy_key, strategy.name,
                        strategy.strategy_type.value, strategy.description,
                        strategy.is_active, strategy.latest_version_id,
                        self._json(strategy.labels),
                        strategy.latest_version_no,
                        strategy.last_7d_return_pct, strategy.last_7d_win_rate,
                        strategy.updated_at, strategy.id,
                    ),
                )
            conn.commit()
            return strategy
        finally:
            self._put_conn(conn)

    # ── strategy versions ─────────────────────────────────────────────────

    def create_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO strategy_versions
                       (id, strategy_id, version_no, schema_version,
                        config_json, config_hash, labels, notes,
                        is_validated, validation_summary, created_by, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        version.id, version.strategy_id, version.version_no,
                        version.schema_version, self._json(version.config_json),
                        version.config_hash, self._json(version.labels),
                        version.notes, version.is_validated,
                        self._json(version.validation_summary),
                        version.created_by, version.created_at,
                    ),
                )
            conn.commit()
            return version
        finally:
            self._put_conn(conn)

    def get_strategy_version(self, version_id: str) -> StrategyVersion | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM strategy_versions WHERE id = %s", (version_id,))
                row = cur.fetchone()
            return _row_to_strategy_version(row) if row else None
        finally:
            self._put_conn(conn)

    def list_strategy_versions_by_ids(self, version_ids: list[str]) -> list[StrategyVersion]:
        if not version_ids:
            return []
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM strategy_versions WHERE id = ANY(%s)",
                    (list(dict.fromkeys(version_ids)),),
                )
                rows = cur.fetchall()
            return [_row_to_strategy_version(r) for r in rows]
        finally:
            self._put_conn(conn)

    def list_strategy_versions(self, strategy_id: str) -> list[StrategyVersion]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM strategy_versions WHERE strategy_id = %s ORDER BY version_no",
                    (strategy_id,),
                )
                rows = cur.fetchall()
            return [_row_to_strategy_version(r) for r in rows]
        finally:
            self._put_conn(conn)

    def update_strategy_version(self, version: StrategyVersion) -> StrategyVersion:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE strategy_versions SET
                       schema_version=%s, config_json=%s, config_hash=%s,
                       labels=%s, notes=%s, is_validated=%s,
                       validation_summary=%s, created_by=%s
                       WHERE id=%s""",
                    (
                        version.schema_version, self._json(version.config_json),
                        version.config_hash, self._json(version.labels),
                        version.notes, version.is_validated,
                        self._json(version.validation_summary),
                        version.created_by, version.id,
                    ),
                )
            conn.commit()
            return version
        finally:
            self._put_conn(conn)

    # ── sessions ──────────────────────────────────────────────────────────

    def create_session(self, session: Session) -> Session:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO sessions
                       (id, mode, status, strategy_version_id,
                        symbol_scope_json, risk_overrides_json, config_snapshot,
                        performance_json, health_json, trace_id,
                        started_at, ended_at, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        session.id, session.mode.value, session.status.value,
                        session.strategy_version_id,
                        self._json(session.symbol_scope_json),
                        self._json(session.risk_overrides_json),
                        self._json(session.config_snapshot),
                        self._json(session.performance_json),
                        self._json(session.health_json),
                        session.trace_id,
                        session.started_at, session.ended_at,
                        session.created_at, session.updated_at,
                    ),
                )
            conn.commit()
            return session
        finally:
            self._put_conn(conn)

    def get_session(self, session_id: str) -> Session | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
                row = cur.fetchone()
            return _row_to_session(row) if row else None
        finally:
            self._put_conn(conn)

    def list_sessions(self) -> list[Session]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM sessions ORDER BY created_at DESC")
                rows = cur.fetchall()
            return [_row_to_session(r) for r in rows]
        finally:
            self._put_conn(conn)

    def update_session_status(self, session_id: str, status: str) -> Session | None:
        now = datetime.now(UTC)
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                ended_clause = ""
                params: list[Any] = [status, now]
                if status in {SessionStatus.STOPPED.value, SessionStatus.FAILED.value}:
                    ended_clause = ", ended_at = %s"
                    params.append(now)
                params.append(session_id)
                cur.execute(
                    f"UPDATE sessions SET status = %s, updated_at = %s{ended_clause} WHERE id = %s RETURNING *",
                    tuple(params),
                )
                row = cur.fetchone()
            conn.commit()
            return _row_to_session(row) if row else None
        finally:
            self._put_conn(conn)

    def update_session(self, session: Session) -> Session:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE sessions SET
                       mode=%s, status=%s, strategy_version_id=%s,
                       symbol_scope_json=%s, risk_overrides_json=%s,
                       config_snapshot=%s, performance_json=%s,
                       health_json=%s, trace_id=%s, started_at=%s,
                       ended_at=%s, updated_at=%s
                       WHERE id=%s""",
                    (
                        session.mode.value,
                        session.status.value,
                        session.strategy_version_id,
                        self._json(session.symbol_scope_json),
                        self._json(session.risk_overrides_json),
                        self._json(session.config_snapshot),
                        self._json(session.performance_json),
                        self._json(session.health_json),
                        session.trace_id,
                        session.started_at,
                        session.ended_at,
                        session.updated_at,
                        session.id,
                    ),
                )
            conn.commit()
            return session
        finally:
            self._put_conn(conn)

    # ── signals ───────────────────────────────────────────────────────────

    def create_signal(self, signal: Signal) -> Signal:
        dedupe_key = f"{signal.session_id}:{signal.symbol}:{signal.snapshot_time.isoformat()}"
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO signals
                       (id, session_id, strategy_version_id, symbol, timeframe,
                        signal_action, confidence, reason_codes, explain_json,
                        blocked, signal_price, snapshot_time, dedupe_key, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (dedupe_key) DO NOTHING""",
                    (
                        signal.id, signal.session_id, signal.strategy_version_id,
                        signal.symbol, signal.timeframe, signal.action,
                        signal.confidence, self._json(signal.reason_codes),
                        self._json(signal.explain_payload), signal.blocked, signal.signal_price,
                        signal.snapshot_time, dedupe_key, datetime.now(UTC),
                    ),
                )
            conn.commit()
            return signal
        finally:
            self._put_conn(conn)

    def list_session_signals(self, session_id: str) -> list[Signal]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM signals WHERE session_id = %s ORDER BY snapshot_time",
                    (session_id,),
                )
                rows = cur.fetchall()
            return [_row_to_signal(r) for r in rows]
        finally:
            self._put_conn(conn)

    # ── positions ─────────────────────────────────────────────────────────

    def list_signals_for_sessions(self, session_ids: list[str]) -> list[Signal]:
        if not session_ids:
            return []
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM signals WHERE session_id = ANY(%s) ORDER BY snapshot_time DESC",
                    (list(dict.fromkeys(session_ids)),),
                )
                rows = cur.fetchall()
            return [_row_to_signal(r) for r in rows]
        finally:
            self._put_conn(conn)

    def create_position(self, position: Position) -> Position:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO positions
                       (id, session_id, strategy_version_id, symbol,
                        position_state, side, entry_time, avg_entry_price,
                        quantity, stop_loss_price, take_profit_price,
                        unrealized_pnl, unrealized_pnl_pct,
                        created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        position.id, position.session_id,
                        position.strategy_version_id, position.symbol,
                        position.position_state.value, position.side,
                        position.entry_time, position.avg_entry_price,
                        position.quantity, position.stop_loss_price,
                        position.take_profit_price, position.unrealized_pnl,
                        position.unrealized_pnl_pct,
                        datetime.now(UTC), datetime.now(UTC),
                    ),
                )
            conn.commit()
            return position
        finally:
            self._put_conn(conn)

    def get_position_by_id(self, position_id: str) -> Position | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM positions WHERE id = %s", (position_id,))
                row = cur.fetchone()
            return _row_to_position(row) if row else None
        finally:
            self._put_conn(conn)

    def list_session_positions(self, session_id: str) -> list[Position]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM positions WHERE session_id = %s ORDER BY created_at",
                    (session_id,),
                )
                rows = cur.fetchall()
            return [_row_to_position(r) for r in rows]
        finally:
            self._put_conn(conn)

    def list_positions_for_sessions(self, session_ids: list[str]) -> list[Position]:
        if not session_ids:
            return []
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM positions WHERE session_id = ANY(%s) ORDER BY created_at DESC",
                    (list(dict.fromkeys(session_ids)),),
                )
                rows = cur.fetchall()
            return [_row_to_position(r) for r in rows]
        finally:
            self._put_conn(conn)

    def update_position(self, position: Position) -> Position:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE positions SET
                       position_state=%s, side=%s, entry_time=%s,
                       avg_entry_price=%s, quantity=%s, stop_loss_price=%s,
                       take_profit_price=%s, unrealized_pnl=%s,
                       unrealized_pnl_pct=%s, updated_at=%s
                       WHERE id=%s""",
                    (
                        position.position_state.value, position.side,
                        position.entry_time, position.avg_entry_price,
                        position.quantity, position.stop_loss_price,
                        position.take_profit_price, position.unrealized_pnl,
                        position.unrealized_pnl_pct, datetime.now(UTC),
                        position.id,
                    ),
                )
            conn.commit()
            return position
        finally:
            self._put_conn(conn)

    # ── orders ────────────────────────────────────────────────────────────

    def create_order(self, order: Order) -> Order:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO orders
                       (id, session_id, strategy_version_id, symbol,
                        order_role, order_type, order_state,
                        requested_price, executed_price, requested_qty,
                        executed_qty, retry_count, idempotency_key,
                        submitted_at, filled_at, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        order.id, order.session_id, order.strategy_version_id,
                        order.symbol, order.order_role, order.order_type,
                        order.order_state.value, order.requested_price,
                        order.executed_price, order.requested_qty,
                        order.executed_qty, order.retry_count,
                        f"idm_{order.id}",
                        order.submitted_at, order.filled_at,
                        datetime.now(UTC), datetime.now(UTC),
                    ),
                )
            conn.commit()
            return order
        finally:
            self._put_conn(conn)

    def list_session_orders(self, session_id: str) -> list[Order]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM orders WHERE session_id = %s ORDER BY created_at",
                    (session_id,),
                )
                rows = cur.fetchall()
            return [_row_to_order(r) for r in rows]
        finally:
            self._put_conn(conn)

    # ── backtest runs ─────────────────────────────────────────────────────

    def create_backtest_run(self, run: BacktestRun) -> BacktestRun:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO backtest_runs
                       (id, strategy_version_id, symbols_json, timeframes_json,
                        date_from, date_to, initial_capital,
                        execution_overrides_json, status, metrics_json,
                        trace_id, queued_at, created_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        run.id, run.strategy_version_id,
                        self._json(run.symbols), self._json(run.timeframes),
                        run.date_from, run.date_to, run.initial_capital,
                        self._json({}), run.status, self._json(run.metrics),
                        f"trc_{uuid.uuid4().hex[:12]}",
                        run.created_at, run.created_at,
                    ),
                )
            conn.commit()
            return run
        finally:
            self._put_conn(conn)

    def get_backtest_run(self, run_id: str) -> BacktestRun | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM backtest_runs WHERE id = %s", (run_id,))
                row = cur.fetchone()
            return _row_to_backtest_run(row) if row else None
        finally:
            self._put_conn(conn)

    def list_backtest_runs(self) -> list[BacktestRun]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT * FROM backtest_runs ORDER BY created_at DESC")
                rows = cur.fetchall()
            return [_row_to_backtest_run(r) for r in rows]
        finally:
            self._put_conn(conn)

    def update_backtest_run(self, run: BacktestRun) -> BacktestRun:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """UPDATE backtest_runs SET
                       status=%s, metrics_json=%s, completed_at=%s
                       WHERE id=%s""",
                    (run.status, self._json(run.metrics), run.completed_at, run.id),
                )
            conn.commit()
            return run
        finally:
            self._put_conn(conn)

    # ── backtest trades ───────────────────────────────────────────────────

    def create_backtest_trades_bulk(self, trades: list[BacktestTrade]) -> list[BacktestTrade]:
        if not trades:
            return trades
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                for t in trades:
                    cur.execute(
                        """INSERT INTO backtest_trades
                           (id, backtest_run_id, symbol, entry_time, exit_time,
                            entry_price, exit_price, qty, pnl, pnl_pct,
                            fee_amount, slippage_amount, exit_reason)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            t.id, t.backtest_run_id, t.symbol,
                            t.entry_time, t.exit_time,
                            t.entry_price, t.exit_price, t.qty,
                            t.pnl, t.pnl_pct, t.fee_amount,
                            t.slippage_amount, t.exit_reason,
                        ),
                    )
            conn.commit()
            return trades
        finally:
            self._put_conn(conn)

    def list_backtest_trades(self, run_id: str) -> list[BacktestTrade]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM backtest_trades WHERE backtest_run_id = %s",
                    (run_id,),
                )
                rows = cur.fetchall()
            return [_row_to_backtest_trade(r) for r in rows]
        finally:
            self._put_conn(conn)

    # ── risk events ───────────────────────────────────────────────────────

    def create_risk_event(self, event: RiskEvent) -> RiskEvent:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO risk_events
                       (id, session_id, strategy_version_id, symbol,
                        event_code, severity, payload_json, message, occurred_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        event.id, event.session_id, event.strategy_version_id,
                        event.symbol, event.code, event.severity,
                        self._json(event.payload_preview),
                        event.message, event.created_at,
                    ),
                )
            conn.commit()
            return event
        finally:
            self._put_conn(conn)

    def list_session_risk_events(self, session_id: str) -> list[RiskEvent]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM risk_events WHERE session_id = %s ORDER BY occurred_at",
                    (session_id,),
                )
                rows = cur.fetchall()
            return [_row_to_risk_event(r) for r in rows]
        finally:
            self._put_conn(conn)

    # ── logs ──────────────────────────────────────────────────────────────

    def list_risk_events_for_sessions(self, session_ids: list[str]) -> list[RiskEvent]:
        if not session_ids:
            return []
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    "SELECT * FROM risk_events WHERE session_id = ANY(%s) ORDER BY occurred_at DESC",
                    (list(dict.fromkeys(session_ids)),),
                )
                rows = cur.fetchall()
            return [_row_to_risk_event(r) for r in rows]
        finally:
            self._put_conn(conn)

    def append_log(self, entry: LogEntry) -> LogEntry:
        table = _LOG_TABLE_MAP.get(entry.channel)
        if table is None:
            raise ValueError(f"Unknown log channel: {entry.channel}")
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""INSERT INTO {table}
                        (level, trace_id, session_id, strategy_version_id, symbol,
                         event_type, message, payload_json, logged_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        RETURNING id""",
                    (
                        entry.level, entry.trace_id, entry.session_id,
                        entry.strategy_version_id, entry.symbol,
                        entry.event_type, entry.message,
                        self._json(entry.payload), entry.logged_at,
                    ),
                )
                new_id = cur.fetchone()[0]
            conn.commit()
            entry_copy = LogEntry(
                id=str(new_id),
                channel=entry.channel,
                level=entry.level,
                trace_id=entry.trace_id,
                mode=entry.mode,
                session_id=entry.session_id,
                strategy_version_id=entry.strategy_version_id,
                symbol=entry.symbol,
                event_type=entry.event_type,
                message=entry.message,
                payload=entry.payload,
                logged_at=entry.logged_at,
            )
            return entry_copy
        finally:
            self._put_conn(conn)

    def query_logs(
        self,
        channel: str,
        session_id: str | None = None,
        strategy_version_id: str | None = None,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        table = _LOG_TABLE_MAP.get(channel)
        if table is None:
            return []
        clauses: list[str] = []
        params: list[Any] = []
        if session_id is not None:
            clauses.append("session_id = %s")
            params.append(session_id)
        if strategy_version_id is not None:
            clauses.append("strategy_version_id = %s")
            params.append(strategy_version_id)
        if symbol is not None:
            clauses.append("symbol = %s")
            params.append(symbol)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute(
                    f"SELECT * FROM {table}{where} ORDER BY logged_at DESC LIMIT %s",
                    tuple(params),
                )
                rows = cur.fetchall()
        finally:
            self._put_conn(conn)

        logs = [_row_to_log_entry(r, channel) for r in rows]
        session_ids = {entry.session_id for entry in logs if entry.session_id}
        session_modes: dict[str, str] = {}

        for current_session_id in session_ids:
            session = self.get_session(current_session_id)
            if session is not None:
                session_modes[current_session_id] = session.mode.value

        for entry in logs:
            entry.mode = session_modes.get(entry.session_id)

        return logs

    # ── universe ──────────────────────────────────────────────────────────

    def get_current_universe(self) -> list[dict[str, object]]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=self._cursor_factory()) as cur:
                cur.execute("SELECT symbol, turnover_24h_krw, surge_score, selected FROM universe_symbols")
                rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            self._put_conn(conn)

    def update_universe(self, symbols: list[str]) -> list[dict[str, object]]:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM universe_symbols")
                for sym in symbols:
                    cur.execute(
                        "INSERT INTO universe_symbols (symbol, selected, updated_at) VALUES (%s, %s, %s)",
                        (sym, True, datetime.now(UTC)),
                    )
            conn.commit()
            return self.get_current_universe()
        finally:
            self._put_conn(conn)

    # ── dual-interface aliases ────────────────────────────────────────────

    get_strategy_by_id = get_strategy
    get_strategy_version_by_id = get_strategy_version
    get_session_by_id = get_session
    list_signals_by_session = list_session_signals
    list_positions_by_session = list_session_positions
    list_orders_by_session = list_session_orders
    list_risk_events_by_session = list_session_risk_events
    get_backtest_run_by_id = get_backtest_run
    list_backtest_trades_by_run = list_backtest_trades
