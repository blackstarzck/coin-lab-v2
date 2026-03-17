from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

from ...core import error_codes
from ...core.logging import get_logger
from ...core.trace import generate_trace_id
from ...domain.entities.market import MarketSnapshot
from ...domain.entities.session import (
    ExitReason,
    FillResult,
    Order,
    OrderIntent,
    OrderRole,
    OrderState,
    OrderType,
    Position,
    PositionState,
    ReentryState,
    Session,
    Signal,
    SignalAction,
    SignalState,
)
from ...domain.entities.strategy_decision import PluginAction
from .fill_engine import FillEngine
from .risk_guard_service import RiskGuardService
from .signal_generator import SignalGenerator

logger = get_logger(__name__)

DEFAULT_INITIAL_CAPITAL = 1_000_000.0
DEFAULT_POSITION_SIZE_MODE = "fixed_percent"
DEFAULT_POSITION_SIZE_VALUE = 0.1


class ExecutionService:
    def __init__(self, risk_guard: RiskGuardService, fill_engine: FillEngine, signal_generator: SignalGenerator) -> None:
        self.risk_guard: RiskGuardService = risk_guard
        self.fill_engine: FillEngine = fill_engine
        self.signal_generator: SignalGenerator = signal_generator
        self._positions: dict[str, Position] = {}
        self._orders: dict[str, Order] = {}
        self._signals: dict[str, Signal] = {}
        self._position_bars: dict[str, int] = {}

    def sync_positions(self, positions: list[Position]) -> None:
        for position in positions:
            self._positions[position.id] = position
            if position.position_state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}:
                self._position_bars.setdefault(position.id, 0)

    def has_open_position(self, session_id: str, symbol: str) -> bool:
        return any(
            position.symbol == symbol
            for position in self._list_open_positions(session_id)
        )

    def process_snapshot(
        self,
        session: Session,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> dict[str, object]:
        self._refresh_reentry_state(session, strategy_config, snapshot)
        open_positions_for_symbol = [
            position
            for position in self._list_open_positions(session.id)
            if position.symbol == snapshot.symbol
        ]
        exits = self.evaluate_exits(session, open_positions_for_symbol, strategy_config, snapshot)
        if exits:
            exit_signal = next(
                (
                    current.get("signal")
                    for current in exits
                    if isinstance(current, dict) and isinstance(current.get("signal"), Signal)
                ),
                None,
            )
            return {
                "accepted": True,
                "signal_state": SignalState.CONSUMED.value,
                "signal": exit_signal,
                "exits": exits,
            }

        signal = self.signal_generator.evaluate(strategy_config, snapshot, session.id, session.strategy_version_id)
        if signal is None:
            return {"accepted": False, "signal_state": SignalState.EXPIRED.value, "reason_codes": ["ENTRY_NOT_MET"]}

        self._signals[signal.id] = signal
        if signal.blocked:
            logger.info("Signal rejected by dedupe", extra={"session_id": session.id, "symbol": signal.symbol})
            return {
                "accepted": False,
                "signal_state": SignalState.REJECTED.value,
                "signal": signal,
                "reason_codes": signal.reason_codes,
            }

        risk_result = self.risk_guard.check_all(session, strategy_config, signal.action, signal.symbol)
        if not risk_result.passed:
            logger.info(
                "Signal blocked by risk guard",
                extra={"session_id": session.id, "symbol": signal.symbol, "blocked_codes": risk_result.blocked_codes},
            )
            self._update_signal_explain(
                signal,
                decision="RISK_BLOCKED",
                reason_codes=list(risk_result.blocked_codes),
                risk_blocks=list(risk_result.blocked_codes),
            )
            return {
                "accepted": False,
                "signal_state": SignalState.REJECTED.value,
                "signal": signal,
                "risk": risk_result,
                "reason_codes": risk_result.blocked_codes,
            }

        if signal.action == SignalAction.ENTER.value:
            entry_result = self.execute_entry(session, signal, strategy_config, snapshot)
            if not bool(entry_result.get("accepted", False)):
                reason_codes = entry_result.get("reason_codes")
                explain_codes = list(reason_codes) if isinstance(reason_codes, list) else signal.reason_codes
                self._update_signal_explain(
                    signal,
                    decision="EXECUTION_REJECTED",
                    reason_codes=explain_codes,
                )
            return {
                "accepted": bool(entry_result.get("accepted", False)),
                "signal_state": SignalState.ACCEPTED.value,
                "signal": signal,
                **entry_result,
            }

        exits = self.evaluate_exits(session, self._list_open_positions(session.id), strategy_config, snapshot)
        return {
            "accepted": True,
            "signal_state": SignalState.CONSUMED.value,
            "signal": signal,
            "exits": exits,
        }

    def execute_entry(
        self,
        session: Session,
        signal: Signal,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> dict[str, object]:
        if self.has_open_position(session.id, signal.symbol):
            logger.info(
                "Entry skipped because an open position already exists",
                extra={"session_id": session.id, "symbol": signal.symbol, "error_code": error_codes.RISK_DUPLICATE_POSITION_BLOCKED},
            )
            return {
                "accepted": False,
                "reason_codes": [error_codes.RISK_DUPLICATE_POSITION_BLOCKED],
            }

        intent = self._create_order_intent(signal, session, strategy_config, snapshot)
        order = Order(
            id=f"ord_{uuid4().hex[:12]}",
            session_id=session.id,
            strategy_version_id=session.strategy_version_id,
            symbol=intent.symbol,
            order_role=intent.order_role,
            order_type=intent.order_type,
            order_state=OrderState.CREATED,
            requested_price=intent.limit_price,
            executed_price=None,
            requested_qty=intent.requested_qty,
            executed_qty=0.0,
            retry_count=0,
            submitted_at=datetime.now(UTC),
            filled_at=None,
        )
        self._orders[order.id] = order

        fill = self._simulate_fill(intent, snapshot, strategy_config)
        if not fill.filled and intent.order_type == OrderType.LIMIT.value:
            fill = self._handle_limit_timeout(intent, strategy_config, snapshot)

        if not fill.filled:
            order.order_state = OrderState.EXPIRED
            logger.info("Order not filled", extra={"session_id": session.id, "symbol": intent.symbol, "order_id": order.id})
            return {
                "accepted": False,
                "order": order,
                "fill": fill,
                "reason_codes": [error_codes.EXEC_LIMIT_NOT_FILLED_TIMEOUT],
            }

        order.order_state = OrderState.FILLED
        order.executed_price = fill.fill_price
        order.executed_qty = fill.fill_qty
        order.filled_at = datetime.now(UTC)

        position = self._update_position_state(
            session=session,
            symbol=intent.symbol,
            side=intent.side,
            qty=fill.fill_qty,
            fill_price=fill.fill_price,
            strategy_config=strategy_config,
            state=PositionState.OPEN,
        )
        self.risk_guard.register_position(session.id, intent.symbol, PositionState.OPEN)
        self._position_bars[position.id] = 0

        logger.info(
            "Entry filled",
            extra={"session_id": session.id, "symbol": intent.symbol, "fill_price": fill.fill_price, "qty": fill.fill_qty},
        )
        return {"accepted": True, "intent": intent, "order": order, "fill": fill, "position": position}

    def evaluate_exits(
        self,
        session: Session,
        positions: list[Position],
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> list[dict[str, object]]:
        exit_cfg_raw = strategy_config.get("exit")
        exit_cfg = exit_cfg_raw if isinstance(exit_cfg_raw, dict) else {}
        results: list[dict[str, object]] = []
        candle = self._resolve_candle(snapshot, strategy_config)
        candle_high = candle["high"]
        candle_low = candle["low"]
        current_price = candle["close"]
        timeframe = self.signal_generator.primary_timeframe(strategy_config)
        snapshot_key = self.signal_generator.snapshot_key(snapshot, timeframe)
        plugin_decision = self.signal_generator.evaluate_plugin_decision(strategy_config, snapshot) if str(strategy_config.get("type", "dsl")) == "plugin" else None

        for position in positions:
            self._position_bars[position.id] = self._position_bars.get(position.id, 0) + 1
            bar_count = self._position_bars[position.id]
            reason = self.fill_engine.evaluate_exit_triggers(
                position=position,
                current_price=current_price,
                candle_high=candle_high,
                candle_low=candle_low,
                exit_config=exit_cfg,
                bar_count=bar_count,
            )
            explain_payload: dict[str, object] | None = None
            reason_codes: list[str] = []
            if reason is None and plugin_decision is not None and plugin_decision.action == PluginAction.EXIT:
                reason = ExitReason.STRATEGY_EXIT
                reason_codes = plugin_decision.reason_codes or [ExitReason.STRATEGY_EXIT.value]
                explain_payload = self.signal_generator.build_plugin_explain_payload(
                    snapshot_key=snapshot_key,
                    decision=plugin_decision,
                    fallback_decision=SignalAction.EXIT.value,
                )
            if reason is None and str(strategy_config.get("type", "dsl")) != "plugin" and isinstance(exit_cfg.get("logic"), str):
                evaluation = self.signal_generator.evaluate_block(
                    exit_cfg,
                    snapshot,
                    path="exit",
                    default_timeframe=timeframe,
                )
                if evaluation.matched:
                    reason = ExitReason.STRATEGY_EXIT
                    reason_codes = evaluation.reason_codes or [ExitReason.STRATEGY_EXIT.value]
                    explain_payload = self.signal_generator.build_explain_payload(
                        snapshot_key=snapshot_key,
                        decision=SignalAction.EXIT.value,
                        result=evaluation,
                    )
            if reason is None:
                continue

            if explain_payload is None:
                reason_codes = [reason.value]
                explain_payload = self._build_exit_explain_payload(
                    snapshot=snapshot,
                    snapshot_key=snapshot_key,
                    exit_config=exit_cfg,
                    position=position,
                    current_price=current_price,
                    reason=reason,
                )

            fill = self.fill_engine.simulate_market_fill(
                base_price=current_price,
                side="SELL",
                slippage_model="fixed_bps",
                slippage_bps=self._as_float(self._as_dict(strategy_config.get("backtest")).get("slippage_bps"), 0.0),
                fee_bps=self._as_float(self._as_dict(strategy_config.get("backtest")).get("fee_bps"), 0.0),
                qty=position.quantity,
            )
            fill.exit_reason = reason.value

            closed_position = self._update_position_state(
                session=session,
                symbol=position.symbol,
                side=position.side,
                qty=position.quantity,
                fill_price=fill.fill_price,
                strategy_config=strategy_config,
                state=PositionState.CLOSED,
                existing_position=position,
            )
            self.risk_guard.register_position(session.id, position.symbol, PositionState.CLOSED)
            self._arm_reentry_guard(session, strategy_config, position.symbol)
            if reason in {ExitReason.STOP_LOSS, ExitReason.STOP_LOSS_INTRA_BAR_CONSERVATIVE, ExitReason.EMERGENCY_KILL}:
                entry = position.avg_entry_price or 0.0
                exit_price = fill.fill_price or entry
                loss = max(0.0, (entry - exit_price) * position.quantity + fill.fee_amount)
                self.risk_guard.record_daily_loss(session.id, loss)

            exit_signal = Signal(
                id=f"sig_{uuid4().hex[:12]}",
                session_id=session.id,
                strategy_version_id=session.strategy_version_id,
                symbol=position.symbol,
                timeframe=timeframe,
                action=SignalAction.EXIT.value,
                signal_price=current_price,
                confidence=1.0,
                reason_codes=reason_codes,
                snapshot_time=snapshot.snapshot_time,
                blocked=False,
                explain_payload=explain_payload,
            )

            results.append(
                {
                    "position": closed_position,
                    "fill": fill,
                    "exit_reason": reason.value,
                    "signal": exit_signal,
                }
            )
        return results

    def _create_order_intent(
        self,
        signal: Signal,
        session: Session,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> OrderIntent:
        execution_cfg = self._as_dict(strategy_config.get("execution"))
        order_type = str(execution_cfg.get("entry_order_type", OrderType.MARKET.value)).upper()
        timeout_sec = self._as_float(execution_cfg.get("limit_timeout_sec"), 15.0)
        fallback_to_market = bool(execution_cfg.get("fallback_to_market", True))
        requested_qty = self._calculate_position_size(strategy_config, snapshot)
        limit_price = snapshot.latest_price if order_type == OrderType.LIMIT.value else None
        return OrderIntent(
            signal_id=signal.id,
            session_id=session.id,
            symbol=signal.symbol,
            side="BUY",
            order_type=order_type,
            order_role=OrderRole.ENTRY.value,
            requested_qty=requested_qty,
            limit_price=limit_price,
            timeout_sec=timeout_sec,
            fallback_to_market=fallback_to_market,
            idempotency_key=f"{session.id}:{signal.id}:{signal.symbol}:{signal.snapshot_time.isoformat()}",
            trace_id=generate_trace_id(),
        )

    def _simulate_fill(self, intent: OrderIntent, snapshot: MarketSnapshot, strategy_config: dict[str, object]) -> FillResult:
        backtest_cfg = self._as_dict(strategy_config.get("backtest"))
        execution_cfg = self._as_dict(strategy_config.get("execution"))
        candle = self._resolve_candle(snapshot, strategy_config)
        base_price = candle["open"] if str(backtest_cfg.get("fill_assumption", "next_bar_open")) == "next_bar_open" else candle["close"]
        slippage_model = str(execution_cfg.get("slippage_model", "fixed_bps"))
        slippage_bps = self._as_float(backtest_cfg.get("slippage_bps"), 0.0)
        fee_bps = self._as_float(backtest_cfg.get("fee_bps"), 0.0)

        if intent.order_type == OrderType.MARKET.value:
            return self.fill_engine.simulate_market_fill(
                base_price=base_price,
                side=intent.side,
                slippage_model=slippage_model,
                slippage_bps=slippage_bps,
                fee_bps=fee_bps,
                qty=intent.requested_qty,
            )

        limit_price = intent.limit_price if intent.limit_price is not None else base_price
        return self.fill_engine.simulate_limit_fill(
            limit_price=limit_price,
            candle_high=candle["high"],
            candle_low=candle["low"],
            side=intent.side,
            fee_bps=fee_bps,
            qty=intent.requested_qty,
        )

    def _handle_limit_timeout(
        self,
        intent: OrderIntent,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> FillResult:
        if not intent.fallback_to_market:
            return FillResult(
                filled=False,
                fill_price=None,
                fill_qty=0.0,
                fee_amount=0.0,
                slippage_amount=0.0,
            )

        backtest_cfg = self._as_dict(strategy_config.get("backtest"))
        execution_cfg = self._as_dict(strategy_config.get("execution"))
        base_price = snapshot.latest_price or 0.0
        logger.info("Limit timeout fallback to market", extra={"symbol": intent.symbol, "error_code": error_codes.EXEC_LIMIT_NOT_FILLED_TIMEOUT})
        return self.fill_engine.simulate_market_fill(
            base_price=base_price,
            side=intent.side,
            slippage_model=str(execution_cfg.get("slippage_model", "fixed_bps")),
            slippage_bps=self._as_float(backtest_cfg.get("slippage_bps"), 0.0),
            fee_bps=self._as_float(backtest_cfg.get("fee_bps"), 0.0),
            qty=intent.requested_qty,
        )

    def _calculate_position_size(self, strategy_config: dict[str, object], snapshot: MarketSnapshot) -> float:
        price = snapshot.latest_price or 0.0
        if price <= 0:
            return 0.0
        pos_cfg = self._as_dict(strategy_config.get("position"))
        size_mode = str(pos_cfg.get("size_mode", DEFAULT_POSITION_SIZE_MODE))
        size_value = self._as_float(pos_cfg.get("size_value"), DEFAULT_POSITION_SIZE_VALUE)
        initial_capital = self._as_float(
            self._as_dict(strategy_config.get("backtest")).get("initial_capital"),
            DEFAULT_INITIAL_CAPITAL,
        )

        if size_mode == "fixed_qty":
            return max(size_value, 0.0)

        if size_mode == "fixed_amount":
            qty = size_value / price
            return max(qty, 0.0)

        if size_mode == "fixed_percent":
            notional = initial_capital * size_value
            qty = notional / price
            return max(qty, 0.0)

        return 0.0

    def _update_position_state(
        self,
        session: Session,
        symbol: str,
        side: str,
        qty: float,
        fill_price: float | None,
        strategy_config: dict[str, object],
        state: PositionState,
        existing_position: Position | None = None,
    ) -> Position:
        now = datetime.now(UTC)
        exit_cfg = self._as_dict(strategy_config.get("exit"))
        if existing_position is None:
            entry_price = fill_price
            stop_loss = None
            take_profit = None
            if entry_price is not None:
                stop_pct = self._as_float(exit_cfg.get("stop_loss_pct"), 0.0)
                tp_pct = self._as_float(exit_cfg.get("take_profit_pct"), 0.0)
                stop_loss = entry_price * (1.0 - stop_pct) if stop_pct > 0 else None
                take_profit = entry_price * (1.0 + tp_pct) if tp_pct > 0 else None
            position = Position(
                id=f"pos_{uuid4().hex[:12]}",
                session_id=session.id,
                strategy_version_id=session.strategy_version_id,
                symbol=symbol,
                position_state=state,
                side=side,
                entry_time=now,
                avg_entry_price=entry_price,
                quantity=qty,
                stop_loss_price=stop_loss,
                take_profit_price=take_profit,
                unrealized_pnl=0.0,
                unrealized_pnl_pct=0.0,
            )
            self._positions[position.id] = position
            return position

        existing_position.position_state = state
        existing_position.quantity = 0.0 if state == PositionState.CLOSED else existing_position.quantity
        self._positions[existing_position.id] = existing_position
        return existing_position

    def _list_open_positions(self, session_id: str) -> list[Position]:
        return [
            pos
            for pos in self._positions.values()
            if pos.session_id == session_id and pos.position_state in {PositionState.OPEN, PositionState.OPENING, PositionState.CLOSING}
        ]

    def _update_signal_explain(
        self,
        signal: Signal,
        *,
        decision: str,
        reason_codes: list[str] | None = None,
        risk_blocks: list[str] | None = None,
    ) -> None:
        payload = dict(signal.explain_payload or {})
        payload["decision"] = decision
        if reason_codes is not None:
            payload["reason_codes"] = list(reason_codes)
        if risk_blocks is not None:
            payload["risk_blocks"] = list(risk_blocks)
        signal.explain_payload = payload

    def _build_exit_explain_payload(
        self,
        *,
        snapshot: MarketSnapshot,
        snapshot_key: str,
        exit_config: dict[str, object],
        position: Position,
        current_price: float,
        reason: ExitReason,
    ) -> dict[str, object]:
        facts: list[dict[str, object]] = [
            {"label": "current_price", "value": current_price},
        ]
        parameters: list[dict[str, object]] = []
        if position.avg_entry_price is not None:
            facts.append({"label": "avg_entry_price", "value": position.avg_entry_price})
        if position.stop_loss_price is not None:
            facts.append({"label": "stop_loss_price", "value": position.stop_loss_price})
        if position.take_profit_price is not None:
            facts.append({"label": "take_profit_price", "value": position.take_profit_price})
        for key in ("stop_loss_pct", "take_profit_pct", "trailing_stop_pct", "time_stop_bars"):
            if key in exit_config:
                parameters.append({"label": f"exit.{key}", "value": exit_config.get(key)})
        return {
            "snapshot_key": snapshot_key,
            "decision": SignalAction.EXIT.value,
            "reason_codes": [reason.value],
            "facts": facts + parameters,
            "parameters": parameters,
            "matched_conditions": [f"exit.{reason.value.lower()}"],
            "failed_conditions": [],
            "risk_blocks": [],
        }

    def _resolve_candle(self, snapshot: MarketSnapshot, strategy_config: dict[str, object]) -> dict[str, float]:
        market = self._as_dict(strategy_config.get("market"))
        tf_raw = market.get("timeframes")
        timeframes = tf_raw if isinstance(tf_raw, list) else []
        timeframe = str(timeframes[0]) if timeframes else "1m"
        candle = snapshot.candles.get(timeframe)
        if candle is None:
            price = snapshot.latest_price or 0.0
            return {"open": price, "high": price, "low": price, "close": price}
        return {"open": candle.open, "high": candle.high, "low": candle.low, "close": candle.close}

    def _as_dict(self, value: object) -> dict[str, object]:
        return cast(dict[str, object], value) if isinstance(value, dict) else {}

    def _as_float(self, value: object, fallback: float) -> float:
        return float(value) if isinstance(value, int | float) else fallback

    def _arm_reentry_guard(self, session: Session, strategy_config: dict[str, object], symbol: str) -> None:
        reentry_cfg = self._as_dict(strategy_config.get("reentry"))
        if not bool(reentry_cfg.get("allow", reentry_cfg.get("enabled", False))):
            return
        self.risk_guard.start_reentry_guard(
            session.id,
            symbol,
            cooldown_bars=self._as_int(reentry_cfg.get("cooldown_bars"), 0),
            require_reset=bool(reentry_cfg.get("require_reset", False)),
        )

    def _refresh_reentry_state(self, session: Session, strategy_config: dict[str, object], snapshot: MarketSnapshot) -> None:
        reentry_cfg = self._as_dict(strategy_config.get("reentry"))
        if not bool(reentry_cfg.get("allow", reentry_cfg.get("enabled", False))):
            return

        state = self.risk_guard.advance_reentry_guard(session.id, snapshot.symbol)
        if state != ReentryState.WAIT_RESET:
            return

        reset_condition = self._as_dict(reentry_cfg.get("reset_condition"))
        if not reset_condition:
            return

        timeframe = self.signal_generator.primary_timeframe(strategy_config)
        evaluation = self.signal_generator.evaluate_block(
            reset_condition,
            snapshot,
            path="reentry.reset_condition",
            default_timeframe=timeframe,
        )
        if evaluation.matched:
            self.risk_guard.clear_reentry_guard(session.id, snapshot.symbol)

    def _as_int(self, value: object, fallback: int) -> int:
        return int(value) if isinstance(value, int | float) else fallback
