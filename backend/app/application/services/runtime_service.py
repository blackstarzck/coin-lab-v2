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
from app.domain.entities.market import ConnectionState, EvaluationTrigger, MarketSnapshot, NormalizedEvent
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
    IDLE_RECONNECT_TIMEOUT_SECONDS: int = 15

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
        self._last_skip_log_at: dict[str, datetime] = {}
        self._last_runtime_event_at: datetime | None = None

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
            "worker_alive": bool(self._thread and self._thread.is_alive()),
            "last_runtime_event_at": self._last_runtime_event_at,
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

    def manual_reevaluate_session(self, session: Session, symbols: list[str] | None = None) -> dict[str, object]:
        requested_symbols = [symbol for symbol in (symbols or []) if symbol]
        active_symbols = [
            str(symbol)
            for symbol in session.symbol_scope_json.get("active_symbols", [])
            if isinstance(symbol, str)
        ]
        target_symbols = requested_symbols or active_symbols
        target_symbols = [symbol for symbol in target_symbols if symbol in active_symbols]

        if session.status != SessionStatus.RUNNING:
            return {
                "accepted": False,
                "session_id": session.id,
                "requested_symbols": target_symbols,
                "evaluated_symbols": [],
                "skipped": [
                    {
                        "symbol": None,
                        "reason_code": "SESSION_NOT_RUNNING",
                        "reason_detail": f"session status is {session.status.value}",
                    }
                ],
            }

        self._sync_session_runtime_state(session)
        evaluated_symbols: list[str] = []
        skipped: list[dict[str, object]] = []

        for symbol in target_symbols:
            snapshot = self.market_ingest_service.build_manual_snapshot(symbol)
            if snapshot is None:
                skipped.append(
                    {
                        "symbol": symbol,
                        "reason_code": error_codes.DATA_REQUIRED_TIMEFRAME_MISSING,
                        "reason_detail": "no market snapshot is available for the symbol",
                    }
                )
                continue

            self.stream_service.record_snapshot(snapshot)
            skip_reason = self._evaluation_skip_reason(session, snapshot, EvaluationTrigger.ON_MANUAL_REEVALUATE)
            if skip_reason is not None:
                reason_code, reason_detail = skip_reason
                skipped.append({"symbol": symbol, "reason_code": reason_code, "reason_detail": reason_detail})
                self._append_strategy_log(
                    session=session,
                    snapshot=snapshot,
                    level="WARNING",
                    event_type="EVALUATION_SKIPPED",
                    message="전략 평가를 건너뛰었습니다",
                    payload={
                        **self._evaluation_payload(EvaluationTrigger.ON_MANUAL_REEVALUATE, snapshot),
                        "reason_code": reason_code,
                        "reason_detail": reason_detail,
                    },
                )
            else:
                self._append_strategy_log(
                    session=session,
                    snapshot=snapshot,
                    level="INFO",
                    event_type="EVALUATION_STARTED",
                    message="전략 평가를 시작했습니다",
                    payload=self._evaluation_payload(EvaluationTrigger.ON_MANUAL_REEVALUATE, snapshot),
                )
                result = self.execution_service.process_snapshot(session, session.config_snapshot, snapshot)
                self._persist_execution_result(session, snapshot, result)
                self._append_strategy_log(
                    session=session,
                    snapshot=snapshot,
                    level="INFO",
                    event_type="EVALUATION_COMPLETED",
                    message="전략 평가가 완료되었습니다",
                    payload={
                        **self._evaluation_payload(EvaluationTrigger.ON_MANUAL_REEVALUATE, snapshot),
                        **self._evaluation_result_payload(result),
                    },
                )
                evaluated_symbols.append(symbol)

            self._refresh_open_positions(session, symbol, snapshot.latest_price)
            self._update_session_health(session, snapshot, trigger=EvaluationTrigger.ON_MANUAL_REEVALUATE)
            self._recalculate_performance(session)

        self.stream_service.publish_monitoring_snapshot(force=True)
        return {
            "accepted": len(evaluated_symbols) > 0,
            "session_id": session.id,
            "requested_symbols": target_symbols,
            "evaluated_symbols": evaluated_symbols,
            "skipped": skipped,
        }

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
        self._last_runtime_event_at = event.received_at
        result = self.market_ingest_service.process_event(event)
        snapshot = result.get("snapshot")
        evaluation_snapshot = result.get("evaluation_snapshot")
        if isinstance(snapshot, MarketSnapshot):
            self.stream_service.record_snapshot(snapshot)
            self._evaluate_sessions_for_snapshot(snapshot, evaluation_snapshot)
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
            self._last_runtime_event_at = datetime.now(UTC)
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
                    if self._should_reconnect_on_idle(datetime.now(UTC)):
                        raise RuntimeError("runtime websocket idle timeout")
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

    def _should_reconnect_on_idle(self, now: datetime) -> bool:
        if self._last_runtime_event_at is None:
            return False
        return (now - self._last_runtime_event_at) >= timedelta(seconds=self.IDLE_RECONNECT_TIMEOUT_SECONDS)

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

    def _evaluate_sessions_for_snapshot(
        self,
        snapshot: MarketSnapshot,
        evaluation_snapshot: MarketSnapshot | None,
    ) -> None:
        for session in self.store.list_sessions():
            if session.status != SessionStatus.RUNNING:
                continue
            active_symbols = session.symbol_scope_json.get("active_symbols", [])
            if snapshot.symbol not in active_symbols:
                continue
            self._sync_session_runtime_state(session)
            trigger = self._resolve_session_trigger(session)
            selected_snapshot = self._candidate_snapshot_for_trigger(session, snapshot, evaluation_snapshot, trigger)
            if selected_snapshot is not None:
                skip_reason = self._evaluation_skip_reason(session, selected_snapshot, trigger)
                if skip_reason is not None:
                    reason_code, reason_detail = skip_reason
                    if self._should_log_evaluation_skip(session.id, selected_snapshot.symbol, trigger, reason_code):
                        self._append_strategy_log(
                            session=session,
                            snapshot=selected_snapshot,
                            level="WARNING",
                            event_type="EVALUATION_SKIPPED",
                            message="전략 평가를 건너뛰었습니다",
                            payload={
                                **self._evaluation_payload(trigger, selected_snapshot),
                                "reason_code": reason_code,
                                "reason_detail": reason_detail,
                            },
                        )
                else:
                    self._mark_evaluation_marker(session, selected_snapshot, trigger)
                    self._append_strategy_log(
                        session=session,
                        snapshot=selected_snapshot,
                        level="INFO",
                        event_type="EVALUATION_STARTED",
                        message="전략 평가를 시작했습니다",
                        payload=self._evaluation_payload(trigger, selected_snapshot),
                    )
                    result = self.execution_service.process_snapshot(session, session.config_snapshot, selected_snapshot)
                    self._persist_execution_result(session, selected_snapshot, result)
                    self._append_strategy_log(
                        session=session,
                        snapshot=selected_snapshot,
                        level="INFO",
                        event_type="EVALUATION_COMPLETED",
                        message="전략 평가가 완료되었습니다",
                        payload={
                            **self._evaluation_payload(trigger, selected_snapshot),
                            **self._evaluation_result_payload(result),
                        },
                    )
            self._refresh_open_positions(session, snapshot.symbol, snapshot.latest_price)
            if self._should_refresh_session_state(session.id, snapshot.snapshot_time):
                self._update_session_health(session, snapshot, trigger=trigger)
                self._recalculate_performance(session)

    def _persist_execution_result(self, session: Session, snapshot: Any, result: dict[str, object]) -> None:
        signal = result.get("signal")
        if isinstance(signal, Signal):
            if self._should_persist_signal(signal):
                self.store.create_signal(signal)
                self._append_strategy_log(
                    session=session,
                    snapshot=snapshot,
                    level="INFO",
                    event_type="SIGNAL_EMITTED",
                    message="진입 신호가 생성되었습니다",
                    payload={
                        "symbol": signal.symbol,
                        "reason_codes": signal.reason_codes,
                        "blocked": signal.blocked,
                        "signal_price": signal.signal_price,
                        "snapshot_time": signal.snapshot_time.isoformat(),
                    },
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
                    self._append_log(
                        channel="risk-control",
                        session=session,
                        symbol=snapshot.symbol,
                        level="WARNING",
                        event_type="SIGNAL_BLOCKED",
                        message=event.message,
                        payload=event.payload_preview,
                        logged_at=event.created_at,
                    )

        order = result.get("order")
        if isinstance(order, Order):
            self.store.create_order(order)
            self._append_log(
                channel="order-simulation",
                session=session,
                symbol=order.symbol,
                level="INFO",
                event_type="ORDER_FILLED" if order.order_state == OrderState.FILLED else "ORDER_CREATED",
                message=f"{order.order_role} 주문 상태: {order.order_state.value.lower()}",
                payload={
                    "requested_qty": order.requested_qty,
                    "executed_qty": order.executed_qty,
                    "executed_price": order.executed_price,
                },
            )

        position = result.get("position")
        if isinstance(position, Position):
            self._save_position(position)

        exits = result.get("exits")
        if isinstance(exits, list):
            for exit_result in exits:
                if not isinstance(exit_result, dict):
                    continue
                exit_signal = exit_result.get("signal")
                exit_position = exit_result.get("position")
                fill = exit_result.get("fill")
                exit_reason = str(exit_result.get("exit_reason", "STRATEGY_EXIT"))
                if isinstance(exit_signal, Signal) and self._should_persist_signal(exit_signal):
                    self.store.create_signal(exit_signal)
                    self._append_strategy_log(
                        session=session,
                        snapshot=snapshot,
                        level="INFO",
                        event_type="SIGNAL_EMITTED",
                        message="청산 신호가 생성되었습니다",
                        payload={
                            "symbol": exit_signal.symbol,
                            "reason_codes": exit_signal.reason_codes,
                            "blocked": exit_signal.blocked,
                            "signal_price": exit_signal.signal_price,
                            "snapshot_time": exit_signal.snapshot_time.isoformat(),
                        },
                    )
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
                    self._append_log(
                        channel="order-simulation",
                        session=session,
                        symbol=exit_position.symbol,
                        level="INFO",
                        event_type="EXIT_FILLED",
                        message=f"{exit_reason} 사유로 청산이 체결되었습니다",
                        payload={"exit_reason": exit_reason},
                    )
                    self._record_realized_pnl(
                        session,
                        exit_position,
                        getattr(fill, "fill_price", None),
                        exit_qty=getattr(fill, "fill_qty", None),
                    )

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

    def _update_session_health(
        self,
        session: Session,
        snapshot: Any,
        *,
        trigger: EvaluationTrigger | None = None,
    ) -> None:
        resolved_trigger = trigger or self._resolve_session_trigger(session)
        snapshot_is_stale = self._is_snapshot_stale_for_session(session, snapshot, resolved_trigger)
        session.health_json = {
            **session.health_json,
            "connection_state": self.stream_service.connection_state,
            "snapshot_consistency": "STALE" if snapshot_is_stale else "HEALTHY",
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

    def _record_realized_pnl(
        self,
        session: Session,
        position: Position,
        exit_price: float | None,
        *,
        exit_qty: float | None = None,
    ) -> None:
        entry_price = position.avg_entry_price or 0.0
        quantity = float(exit_qty) if isinstance(exit_qty, int | float) else position.quantity
        if entry_price <= 0 or exit_price is None or quantity <= 0:
            return
        direction = 1.0 if position.side.upper() in {"LONG", "BUY"} else -1.0
        pnl = (exit_price - entry_price) * quantity * direction
        realized_pnl = float(session.performance_json.get("realized_pnl", 0.0)) + pnl
        trade_count = int(session.performance_json.get("trade_count", 0)) + 1
        winning_trade_count = int(session.performance_json.get("winning_trade_count", 0))
        if pnl > 0:
            winning_trade_count += 1
        symbol_performance = self._symbol_performance_snapshot(session)
        symbol_metrics = symbol_performance.get(position.symbol, {})
        symbol_cost_basis = float(symbol_metrics.get("realized_cost_basis", 0.0)) + (entry_price * quantity)
        symbol_realized_pnl = float(symbol_metrics.get("realized_pnl", 0.0)) + pnl
        symbol_trade_count = int(symbol_metrics.get("trade_count", 0)) + 1
        symbol_winning_trade_count = int(symbol_metrics.get("winning_trade_count", 0))
        if pnl > 0:
            symbol_winning_trade_count += 1
        symbol_performance[position.symbol] = {
            **symbol_metrics,
            "realized_pnl": symbol_realized_pnl,
            "realized_pnl_pct": (symbol_realized_pnl / symbol_cost_basis) * 100 if symbol_cost_basis else 0.0,
            "realized_cost_basis": symbol_cost_basis,
            "trade_count": symbol_trade_count,
            "winning_trade_count": symbol_winning_trade_count,
        }
        session.performance_json = {
            **session.performance_json,
            "realized_pnl": realized_pnl,
            "trade_count": trade_count,
            "winning_trade_count": winning_trade_count,
            "symbol_performance": symbol_performance,
        }
        session.updated_at = datetime.now(UTC)
        self.store.update_session(session)

    def _symbol_performance_snapshot(self, session: Session) -> dict[str, dict[str, float | int]]:
        raw_metrics = session.performance_json.get("symbol_performance")
        if not isinstance(raw_metrics, dict):
            return {}
        snapshot: dict[str, dict[str, float | int]] = {}
        for symbol, metrics in raw_metrics.items():
            if not isinstance(symbol, str) or not isinstance(metrics, dict):
                continue
            snapshot[symbol] = dict(metrics)
        return snapshot

    def _append_strategy_log(
        self,
        *,
        session: Session,
        snapshot: MarketSnapshot,
        level: str,
        event_type: str,
        message: str,
        payload: dict[str, object],
    ) -> None:
        self._append_log(
            channel="strategy-execution",
            session=session,
            symbol=snapshot.symbol,
            level=level,
            event_type=event_type,
            message=message,
            payload=payload,
        )

    def _append_log(
        self,
        *,
        channel: str,
        session: Session,
        symbol: str,
        level: str,
        event_type: str,
        message: str,
        payload: dict[str, object],
        logged_at: datetime | None = None,
    ) -> None:
        self.store.append_log(
            LogEntry(
                id=f"log_{uuid4().hex[:12]}",
                channel=channel,
                level=level,
                event_type=event_type,
                message=message,
                payload=payload,
                logged_at=logged_at or datetime.now(UTC),
                session_id=session.id,
                strategy_version_id=session.strategy_version_id,
                symbol=symbol,
                trace_id=session.trace_id,
                mode=session.mode.value,
            )
        )

    def _evaluation_payload(self, trigger: EvaluationTrigger, snapshot: MarketSnapshot) -> dict[str, object]:
        return {
            "trigger": trigger.value,
            "snapshot_time": snapshot.snapshot_time.isoformat(),
            "source_event_type": snapshot.source_event_type.value if snapshot.source_event_type is not None else None,
            "source_trace_ids": list(snapshot.trigger_trace_ids),
            "closed_timeframes": list(snapshot.closed_timeframes),
            "updated_timeframes": list(snapshot.updated_timeframes),
        }

    def _evaluation_result_payload(self, result: dict[str, object]) -> dict[str, object]:
        signal = result.get("signal")
        risk_result = result.get("risk")
        blocked_codes = list(getattr(risk_result, "blocked_codes", [])) if risk_result is not None else []
        reason_codes_raw = result.get("reason_codes")
        reason_codes = list(reason_codes_raw) if isinstance(reason_codes_raw, list) else []

        decision = "NO_SIGNAL"
        if isinstance(signal, Signal):
            decision = "SIGNAL_EMITTED"
            if signal.action == "EXIT":
                decision = "EXIT_SIGNAL_EMITTED"
            if signal.blocked:
                decision = "SIGNAL_DEDUPED"
            elif blocked_codes:
                decision = "RISK_BLOCKED"
            elif not bool(result.get("accepted", False)):
                decision = "EXECUTION_REJECTED"
            elif isinstance(result.get("order"), Order):
                decision = "ORDER_FLOW_STARTED"
            elif isinstance(result.get("exits"), list) and signal.action == "EXIT":
                decision = "EXIT_FLOW_STARTED"

        return {
            "decision": decision,
            "accepted": bool(result.get("accepted", False)),
            "signal_state": result.get("signal_state"),
            "reason_codes": reason_codes,
            "blocked_codes": blocked_codes,
        }

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

    def _resolve_session_trigger(self, session: Session) -> EvaluationTrigger:
        market_cfg = session.config_snapshot.get("market")
        market = market_cfg if isinstance(market_cfg, dict) else {}
        configured = market.get("trigger") or market.get("evaluation_trigger")
        if isinstance(configured, str):
            try:
                return EvaluationTrigger(configured.upper())
            except ValueError:
                pass
        return EvaluationTrigger.ON_CANDLE_CLOSE

    def _primary_timeframe(self, session: Session) -> str:
        market_cfg = session.config_snapshot.get("market")
        market = market_cfg if isinstance(market_cfg, dict) else {}
        timeframes = market.get("timeframes") if isinstance(market.get("timeframes"), list) else []
        return str(timeframes[0]) if timeframes else "1m"

    def _candidate_snapshot_for_trigger(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        evaluation_snapshot: MarketSnapshot | None,
        trigger: EvaluationTrigger,
    ) -> MarketSnapshot | None:
        primary_timeframe = self._primary_timeframe(session)

        if trigger == EvaluationTrigger.ON_CANDLE_CLOSE:
            if evaluation_snapshot is None or primary_timeframe not in evaluation_snapshot.closed_timeframes:
                return None
            return evaluation_snapshot

        if trigger == EvaluationTrigger.ON_CANDLE_UPDATE:
            if trigger not in snapshot.available_triggers or primary_timeframe not in snapshot.updated_timeframes:
                return None
            return snapshot

        if trigger == EvaluationTrigger.ON_TICK_BATCH:
            if trigger not in snapshot.available_triggers:
                return None
            return snapshot

        return None

    def _evaluation_skip_reason(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        trigger: EvaluationTrigger,
    ) -> tuple[str, str] | None:
        if snapshot.connection_state == ConnectionState.DEGRADED:
            return (error_codes.DATA_SYMBOL_DEGRADED, "runtime connection is degraded")

        if self._is_snapshot_stale_for_session(session, snapshot, trigger):
            return (error_codes.EXEC_SNAPSHOT_STALE, "snapshot freshness threshold exceeded")

        if trigger != EvaluationTrigger.ON_MANUAL_REEVALUATE and self._has_evaluation_marker(session, snapshot, trigger):
            return ("TRIGGER_COALESCED", "newer evaluation already exists for the same evaluation window")

        return None

    def _has_evaluation_marker(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        trigger: EvaluationTrigger,
    ) -> bool:
        marker = self._evaluation_marker(session, snapshot, trigger)
        key = self._evaluation_marker_key(session, snapshot, trigger)
        return self._last_evaluation_markers.get(key) == marker

    def _mark_evaluation_marker(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        trigger: EvaluationTrigger,
    ) -> None:
        key = self._evaluation_marker_key(session, snapshot, trigger)
        self._last_evaluation_markers[key] = self._evaluation_marker(session, snapshot, trigger)

    def _evaluation_marker_key(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        trigger: EvaluationTrigger,
    ) -> str:
        primary_timeframe = self._primary_timeframe(session)
        return f"{session.id}:{snapshot.symbol}:{primary_timeframe}:{trigger.value}"

    def _evaluation_marker(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        trigger: EvaluationTrigger,
    ) -> str:
        primary_timeframe = self._primary_timeframe(session)
        if trigger == EvaluationTrigger.ON_CANDLE_CLOSE:
            candle = snapshot.candles.get(primary_timeframe)
            if candle is None:
                return snapshot.snapshot_time.isoformat()
            marker = candle.candle_start.isoformat()
        else:
            marker = snapshot.snapshot_time.isoformat()
        return marker

    def _is_snapshot_stale_for_session(
        self,
        session: Session,
        snapshot: MarketSnapshot,
        trigger: EvaluationTrigger,
    ) -> bool:
        basis = "tick" if trigger == EvaluationTrigger.ON_TICK_BATCH else self._primary_timeframe(session)
        return self.market_ingest_service.is_snapshot_stale(snapshot.snapshot_time, basis)

    def _should_refresh_session_state(self, session_id: str, snapshot_time: datetime) -> bool:
        last_refresh_at = self._last_session_refresh_at.get(session_id)
        now = datetime.now(UTC)
        if last_refresh_at is not None and now - last_refresh_at < timedelta(seconds=2):
            return False
        self._last_session_refresh_at[session_id] = now
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

    def _should_log_evaluation_skip(
        self,
        session_id: str,
        symbol: str,
        trigger: EvaluationTrigger,
        reason_code: str,
    ) -> bool:
        if reason_code != error_codes.EXEC_SNAPSHOT_STALE:
            return True
        now = datetime.now(UTC)
        key = f"{session_id}:{symbol}:{trigger.value}:{reason_code}"
        last_logged_at = self._last_skip_log_at.get(key)
        if last_logged_at is not None and now - last_logged_at < timedelta(seconds=60):
            return False
        self._last_skip_log_at[key] = now
        return True
