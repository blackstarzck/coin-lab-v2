from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
import threading
from typing import Any
from uuid import uuid4

import websockets

from app.core import error_codes
from app.core.config import Settings
from app.core.logging import get_logger
from app.domain.entities.market import ConnectionState, NormalizedEvent
from app.domain.entities.session import (
    Order,
    OrderRole,
    OrderState,
    OrderType,
    Position,
    PositionState,
    RiskEvent,
    Session,
    SessionStatus,
    Signal,
    LogEntry,
)
from app.infrastructure.repositories.lab_store import LabStore
from app.infrastructure.upbit.websocket_adapter import UpbitWebsocketAdapter

from .execution_service import ExecutionService
from .market_ingest_service import MarketIngestService
from .stream_service import StreamService

logger = get_logger(__name__)


class RuntimeService:
    def __init__(
        self,
        settings: Settings,
        store: LabStore,
        stream_service: StreamService,
        market_ingest_service: MarketIngestService,
        execution_service: ExecutionService,
    ) -> None:
        self.settings = settings
        self.store = store
        self.stream_service = stream_service
        self.market_ingest_service = market_ingest_service
        self.execution_service = execution_service
        self.adapter = UpbitWebsocketAdapter()
        self.running = True
        self._shutdown = threading.Event()
        self._thread: threading.Thread | None = None
        self._runtime_loop: asyncio.AbstractEventLoop | None = None
        self._active_socket: Any = None
        self._reconnect_count_1h = 0
        self._late_event_counts: dict[str, int] = {}
        self._last_subscription: tuple[str, ...] = ()
        self._last_evaluation_markers: dict[str, str] = {}
        self._last_session_refresh_at: dict[str, datetime] = {}
        self._last_signal_fingerprints: dict[str, str] = {}
        self._last_risk_fingerprints: dict[str, str] = {}

    async def startup(self) -> None:
        if self.settings.app_env == "test":
            self.running = False
            self.stream_service.set_runtime_state(ConnectionState.DISCONNECTED.value, self._reconnect_count_1h)
            return
        self.running = True
        self._start_worker_if_needed()
        await asyncio.sleep(0)

    async def shutdown(self) -> None:
        self._shutdown.set()
        self.running = False
        self._close_active_socket()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None
        self._runtime_loop = None
        self.stream_service.set_runtime_state(ConnectionState.DISCONNECTED.value, self._reconnect_count_1h)

    def status(self) -> dict[str, object]:
        sessions = self.store.list_sessions()
        running_sessions = [item for item in sessions if str(getattr(item.status, "value", item.status)) == "RUNNING"]
        return {
            "running": self.running,
            "store_backend": self.settings.store_backend,
            "session_count": len(sessions),
            "running_session_count": len(running_sessions),
            "active_symbols": list(self._desired_symbols()),
            "connection_state": self.stream_service.connection_state,
            "reconnect_count_1h": self._reconnect_count_1h,
        }

    def start(self) -> dict[str, object]:
        self.running = True
        if self.settings.app_env != "test":
            self._start_worker_if_needed()
        return {"accepted": True, "status": "started"}

    def stop(self) -> dict[str, object]:
        self.running = False
        self._close_active_socket()
        self.stream_service.set_runtime_state(ConnectionState.DISCONNECTED.value, self._reconnect_count_1h)
        return {"accepted": True, "status": "stopped"}

    def _start_worker_if_needed(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._run_worker, name="coin-lab-runtime", daemon=True)
        self._thread.start()

    def _run_worker(self) -> None:
        asyncio.run(self._run_loop())

    def _close_active_socket(self) -> None:
        if self._active_socket is None or self._runtime_loop is None or self._runtime_loop.is_closed():
            return
        future = asyncio.run_coroutine_threadsafe(self._active_socket.close(), self._runtime_loop)
        try:
            future.result(timeout=2)
        except Exception:
            pass

    def ingest_normalized_event(self, event: NormalizedEvent) -> dict[str, object]:
        result = self.market_ingest_service.process_event(event)
        snapshot = self.market_ingest_service.snapshots.get(event.symbol)
        if snapshot is not None:
            self.stream_service.record_snapshot(snapshot)
            self._evaluate_sessions_for_snapshot(snapshot)
            self.stream_service.publish_monitoring_snapshot()

        if not bool(result.get("accepted", False)):
            self._mark_late_events(event.symbol)
        return result

    async def _run_loop(self) -> None:
        self._runtime_loop = asyncio.get_running_loop()
        attempt = 0
        try:
            while not self._shutdown.is_set():
                self._finalize_stopping_sessions()
                if not self.running:
                    self.stream_service.set_runtime_state(ConnectionState.DISCONNECTED.value, self._reconnect_count_1h)
                    await asyncio.sleep(0.5)
                    continue

                desired_symbols = self._desired_symbols()
                if not desired_symbols:
                    self.stream_service.set_runtime_state(ConnectionState.DISCONNECTED.value, self._reconnect_count_1h)
                    await asyncio.sleep(0.5)
                    continue

                try:
                    await self._connect_and_consume(desired_symbols)
                    attempt = 0
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    attempt += 1
                    self._reconnect_count_1h += 1
                    logger.warning("Realtime runtime reconnecting: %s", exc)
                    self.stream_service.set_runtime_state(ConnectionState.RECONNECTING.value, self._reconnect_count_1h)
                    await asyncio.sleep(self.market_ingest_service.get_reconnect_delay(attempt))
        finally:
            self._runtime_loop = None

    async def _connect_and_consume(self, symbols: tuple[str, ...]) -> None:
        payload = self.adapter.build_subscription_payload(list(symbols), ["trade"])
        self._last_subscription = symbols
        async with websockets.connect(
            self.settings.upbit_ws_public_url,
            ping_interval=20,
            ping_timeout=20,
            max_queue=512,
        ) as websocket:
            self._active_socket = websocket
            await websocket.send(json.dumps(payload))
            self.stream_service.set_runtime_state(ConnectionState.CONNECTED.value, self._reconnect_count_1h)
            logger.info("Realtime runtime subscribed to %s", ",".join(symbols))

            while not self._shutdown.is_set() and self.running:
                current_symbols = self._desired_symbols()
                if current_symbols != symbols:
                    break

                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                except TimeoutError:
                    continue

                message = self._decode_message(raw_message)
                if message is None:
                    continue
                normalized = self.adapter.normalize_message(message, datetime.now(UTC))
                if normalized is None:
                    continue
                self.ingest_normalized_event(normalized)
                await asyncio.sleep(0)

        self._active_socket = None

    def _decode_message(self, raw_message: object) -> dict[str, object] | None:
        if isinstance(raw_message, bytes):
            try:
                raw_message = raw_message.decode("utf-8")
            except UnicodeDecodeError:
                return None
        if not isinstance(raw_message, str):
            return None
        try:
            decoded = json.loads(raw_message)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, dict) else None

    def _desired_symbols(self) -> tuple[str, ...]:
        symbols: set[str] = set()
        for session in self.store.list_sessions():
            if session.status != SessionStatus.RUNNING:
                continue
            active_symbols = session.symbol_scope_json.get("active_symbols")
            if isinstance(active_symbols, list):
                symbols.update(str(symbol) for symbol in active_symbols if isinstance(symbol, str))
        return tuple(sorted(symbols))

    def _evaluate_sessions_for_snapshot(self, snapshot: Any) -> None:
        for session in self.store.list_sessions():
            if session.status != SessionStatus.RUNNING:
                continue
            active_symbols = session.symbol_scope_json.get("active_symbols", [])
            if snapshot.symbol not in active_symbols:
                continue
            self._sync_session_runtime_state(session)
            if self._should_evaluate_session(session, snapshot):
                result = self.execution_service.process_snapshot(session, session.config_snapshot, snapshot)
                self._persist_execution_result(session, snapshot, result)
            self._refresh_open_positions(session, snapshot.symbol, snapshot.latest_price)
            if self._should_refresh_session_state(session.id, snapshot.snapshot_time):
                self._update_session_health(session, snapshot)
                self._recalculate_performance(session)

    def _persist_execution_result(self, session: Session, snapshot: Any, result: dict[str, object]) -> None:
        signal = result.get("signal")
        if isinstance(signal, Signal):
            if self._should_persist_signal(signal):
                self.store.create_signal(signal)
                self.store.append_log(
                    LogEntry(
                        id=f"log_{uuid4().hex[:12]}",
                        channel="strategy-execution",
                        level="INFO",
                        event_type="SIGNAL_EVALUATED",
                        message="전략 신호를 평가했습니다",
                        payload={
                            "symbol": signal.symbol,
                            "reason_codes": signal.reason_codes,
                            "blocked": signal.blocked,
                        },
                        logged_at=datetime.now(UTC),
                        session_id=session.id,
                        strategy_version_id=session.strategy_version_id,
                        symbol=signal.symbol,
                        trace_id=session.trace_id,
                        mode=session.mode.value,
                    )
                )

        risk_result = result.get("risk")
        if risk_result is not None and hasattr(risk_result, "blocked_codes"):
            blocked_codes = list(getattr(risk_result, "blocked_codes", []))
            if self._should_persist_risk_block(session.id, snapshot.symbol, blocked_codes):
                for code in blocked_codes:
                    event = RiskEvent(
                        id=f"rsk_{uuid4().hex[:12]}",
                        session_id=session.id,
                        strategy_version_id=session.strategy_version_id,
                        severity="WARN",
                        code=str(code),
                        symbol=snapshot.symbol,
                        message=f"{snapshot.symbol} 신호가 리스크 규칙에 의해 차단되었습니다",
                        payload_preview={"blocked_codes": blocked_codes},
                        created_at=datetime.now(UTC),
                    )
                    self.store.create_risk_event(event)
                    self.store.append_log(
                        LogEntry(
                            id=f"log_{uuid4().hex[:12]}",
                            channel="risk-control",
                            level="WARNING",
                            event_type="SIGNAL_BLOCKED",
                            message=event.message,
                            payload=event.payload_preview,
                            logged_at=event.created_at,
                            session_id=session.id,
                            strategy_version_id=session.strategy_version_id,
                            symbol=snapshot.symbol,
                            trace_id=session.trace_id,
                            mode=session.mode.value,
                        )
                    )

        order = result.get("order")
        if isinstance(order, Order):
            self.store.create_order(order)
            self.store.append_log(
                LogEntry(
                    id=f"log_{uuid4().hex[:12]}",
                    channel="order-simulation",
                    level="INFO",
                    event_type="ORDER_FILLED" if order.order_state == OrderState.FILLED else "ORDER_CREATED",
                    message=f"{order.order_role} 주문 상태: {order.order_state.value.lower()}",
                    payload={
                        "requested_qty": order.requested_qty,
                        "executed_qty": order.executed_qty,
                        "executed_price": order.executed_price,
                    },
                    logged_at=datetime.now(UTC),
                    session_id=session.id,
                    strategy_version_id=session.strategy_version_id,
                    symbol=order.symbol,
                    trace_id=session.trace_id,
                    mode=session.mode.value,
                )
            )

        position = result.get("position")
        if isinstance(position, Position):
            self._save_position(position)

        exits = result.get("exits")
        if isinstance(exits, list):
            for exit_result in exits:
                if not isinstance(exit_result, dict):
                    continue
                exit_position = exit_result.get("position")
                fill = exit_result.get("fill")
                exit_reason = str(exit_result.get("exit_reason", "STRATEGY_EXIT"))
                if isinstance(exit_position, Position):
                    self._save_position(exit_position)
                    exit_order = Order(
                        id=f"ord_{uuid4().hex[:12]}",
                        session_id=session.id,
                        strategy_version_id=session.strategy_version_id,
                        symbol=exit_position.symbol,
                        order_role=OrderRole.EXIT.value,
                        order_type=OrderType.MARKET.value,
                        order_state=OrderState.FILLED,
                        requested_price=getattr(fill, "fill_price", None),
                        executed_price=getattr(fill, "fill_price", None),
                        requested_qty=getattr(fill, "fill_qty", exit_position.quantity),
                        executed_qty=getattr(fill, "fill_qty", exit_position.quantity),
                        retry_count=0,
                        submitted_at=datetime.now(UTC),
                        filled_at=datetime.now(UTC),
                    )
                    self.store.create_order(exit_order)
                    self.store.append_log(
                        LogEntry(
                            id=f"log_{uuid4().hex[:12]}",
                            channel="order-simulation",
                            level="INFO",
                            event_type="EXIT_FILLED",
                            message=f"{exit_reason} 사유로 청산이 체결되었습니다",
                            payload={"exit_reason": exit_reason},
                            logged_at=datetime.now(UTC),
                            session_id=session.id,
                            strategy_version_id=session.strategy_version_id,
                            symbol=exit_position.symbol,
                            trace_id=session.trace_id,
                            mode=session.mode.value,
                        )
                    )
                    self._record_realized_pnl(session, exit_position, getattr(fill, "fill_price", None))

    def _save_position(self, position: Position) -> None:
        existing_positions = self.store.list_session_positions(position.session_id)
        if any(existing.id == position.id for existing in existing_positions):
            self.store.update_position(position)
        else:
            self.store.create_position(position)

    def _sync_session_runtime_state(self, session: Session) -> None:
        positions = self.store.list_session_positions(session.id)
        self.execution_service.sync_positions(positions)
        self.execution_service.risk_guard.sync_open_positions(session.id, positions)

    def _refresh_open_positions(self, session: Session, symbol: str, latest_price: float | None) -> None:
        if latest_price is None:
            return
        for position in self.store.list_session_positions(session.id):
            if position.symbol != symbol:
                continue
            if position.position_state not in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}:
                continue
            entry_price = position.avg_entry_price or 0.0
            if entry_price <= 0:
                continue
            position.unrealized_pnl = (latest_price - entry_price) * position.quantity
            position.unrealized_pnl_pct = ((latest_price - entry_price) / entry_price) * 100
            self.store.update_position(position)

    def _update_session_health(self, session: Session, snapshot: Any) -> None:
        session.health_json = {
            **session.health_json,
            "connection_state": self.stream_service.connection_state,
            "snapshot_consistency": "STALE" if snapshot.is_stale else "HEALTHY",
            "late_event_count_5m": self._late_event_counts.get(session.id, 0),
            "reconnect_count_1h": self._reconnect_count_1h,
        }
        session.updated_at = datetime.now(UTC)
        self.store.update_session(session)

    def _recalculate_performance(self, session: Session) -> None:
        positions = self.store.list_session_positions(session.id)
        initial_capital = float(session.performance_json.get("initial_capital", 1_000_000))
        realized_pnl = float(session.performance_json.get("realized_pnl", 0.0))
        unrealized_pnl = sum(
            position.unrealized_pnl
            for position in positions
            if position.position_state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}
        )
        trade_count = int(session.performance_json.get("trade_count", 0))
        winning_trade_count = int(session.performance_json.get("winning_trade_count", 0))
        equity = initial_capital + realized_pnl + unrealized_pnl
        peak_equity = max(float(session.performance_json.get("peak_equity", initial_capital)), equity)
        drawdown_pct = ((equity - peak_equity) / peak_equity) * 100 if peak_equity else 0.0
        max_drawdown_pct = min(float(session.performance_json.get("max_drawdown_pct", 0.0)), drawdown_pct)

        session.performance_json = {
            **session.performance_json,
            "initial_capital": initial_capital,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": (realized_pnl / initial_capital) * 100 if initial_capital else 0.0,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": (unrealized_pnl / initial_capital) * 100 if initial_capital else 0.0,
            "trade_count": trade_count,
            "win_rate_pct": (winning_trade_count / trade_count) * 100 if trade_count else 0.0,
            "winning_trade_count": winning_trade_count,
            "peak_equity": peak_equity,
            "max_drawdown_pct": max_drawdown_pct,
        }
        session.updated_at = datetime.now(UTC)
        self.store.update_session(session)

    def _record_realized_pnl(self, session: Session, position: Position, exit_price: float | None) -> None:
        entry_price = position.avg_entry_price or 0.0
        if entry_price <= 0 or exit_price is None:
            return
        pnl = (exit_price - entry_price) * position.quantity
        realized_pnl = float(session.performance_json.get("realized_pnl", 0.0)) + pnl
        trade_count = int(session.performance_json.get("trade_count", 0)) + 1
        winning_trade_count = int(session.performance_json.get("winning_trade_count", 0))
        if pnl > 0:
            winning_trade_count += 1
        session.performance_json = {
            **session.performance_json,
            "realized_pnl": realized_pnl,
            "trade_count": trade_count,
            "winning_trade_count": winning_trade_count,
        }
        session.updated_at = datetime.now(UTC)
        self.store.update_session(session)

    def _mark_late_events(self, symbol: str) -> None:
        for session in self.store.list_sessions():
            if session.status != SessionStatus.RUNNING:
                continue
            active_symbols = session.symbol_scope_json.get("active_symbols", [])
            if symbol in active_symbols:
                self._late_event_counts[session.id] = self._late_event_counts.get(session.id, 0) + 1

    def _finalize_stopping_sessions(self) -> None:
        changed = False
        for session in self.store.list_sessions():
            if session.status != SessionStatus.STOPPING:
                continue
            session.status = SessionStatus.STOPPED
            session.ended_at = datetime.now(UTC)
            session.updated_at = datetime.now(UTC)
            self.store.update_session(session)
            changed = True
        if changed:
            self.stream_service.publish_monitoring_snapshot(force=True)

    def _should_evaluate_session(self, session: Session, snapshot: Any) -> bool:
        market_cfg = session.config_snapshot.get("market")
        market = market_cfg if isinstance(market_cfg, dict) else {}
        trade_basis = str(market.get("trade_basis", "candle")).lower()
        timeframes = market.get("timeframes") if isinstance(market.get("timeframes"), list) else []
        primary_timeframe = str(timeframes[0]) if timeframes else "1m"

        if trade_basis == "candle":
            candle = snapshot.candles.get(primary_timeframe)
            marker = candle.candle_start.isoformat() if candle is not None else snapshot.snapshot_time.replace(second=0, microsecond=0).isoformat()
        else:
            marker = snapshot.snapshot_time.replace(microsecond=0).isoformat()

        key = f"{session.id}:{snapshot.symbol}:{primary_timeframe}:{trade_basis}"
        if self._last_evaluation_markers.get(key) == marker:
            return False
        self._last_evaluation_markers[key] = marker
        return True

    def _should_refresh_session_state(self, session_id: str, snapshot_time: datetime) -> bool:
        last_refresh_at = self._last_session_refresh_at.get(session_id)
        if last_refresh_at is not None and snapshot_time - last_refresh_at < timedelta(seconds=2):
            return False
        self._last_session_refresh_at[session_id] = snapshot_time
        return True

    def _should_persist_signal(self, signal: Signal) -> bool:
        fingerprint = "|".join(
            [
                signal.action,
                "blocked" if signal.blocked else "accepted",
                ",".join(signal.reason_codes),
            ]
        )
        key = f"{signal.session_id}:{signal.symbol}:{signal.action}"
        if signal.blocked and signal.reason_codes == [error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED]:
            return False
        if signal.blocked and self._last_signal_fingerprints.get(key) == fingerprint:
            return False
        self._last_signal_fingerprints[key] = fingerprint
        return True

    def _should_persist_risk_block(self, session_id: str, symbol: str, blocked_codes: list[str]) -> bool:
        fingerprint = ",".join(sorted(str(code) for code in blocked_codes))
        key = f"{session_id}:{symbol}"
        if self._last_risk_fingerprints.get(key) == fingerprint:
            return False
        self._last_risk_fingerprints[key] = fingerprint
        return True
