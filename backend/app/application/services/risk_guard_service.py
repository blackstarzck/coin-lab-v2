from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from ...core import error_codes
from ...core.logging import get_logger
from ...domain.entities.session import (
    ExecutionMode,
    Position,
    PositionState,
    ReentryState,
    RiskCheckResult,
    RiskState,
    Session,
    SessionStatus,
    SignalAction,
)

logger = get_logger(__name__)


class RiskGuardService:
    def __init__(self) -> None:
        self._risk_states: dict[str, RiskState] = {}
        self._daily_loss: dict[str, float] = {}
        self._open_positions: dict[str, dict[str, PositionState]] = {}
        self._reentry_states: dict[str, dict[str, ReentryState]] = {}
        self._signal_dedupe: dict[str, datetime] = {}

    def check_all(self, session: Session, strategy_config: dict[str, object], signal_action: str, symbol: str) -> RiskCheckResult:
        risk_cfg = self._as_dict(strategy_config.get("risk"))
        pos_cfg = self._as_dict(strategy_config.get("position"))
        reentry_cfg = self._as_dict(strategy_config.get("reentry"))

        # 1) session_active
        if session.status != SessionStatus.RUNNING:
            return self._block(session.id, error_codes.EXEC_POSITION_STATE_INVALID)

        # 2) mode_allowed
        if not self._is_action_allowed_for_mode(session.mode, signal_action):
            return self._block(session.id, error_codes.EXEC_POSITION_STATE_INVALID)

        # 3) duplicate_entry
        if signal_action == SignalAction.ENTER.value:
            if bool(risk_cfg.get("prevent_duplicate_entry", False)) and self._has_open_position(session.id, symbol):
                return self._block(session.id, error_codes.RISK_DUPLICATE_POSITION_BLOCKED)
            if self._is_duplicate_signal(session.id, symbol, signal_action):
                return self._block(session.id, error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED)

        # 4) max_open_positions
        if signal_action == SignalAction.ENTER.value:
            max_per_symbol = self._as_int(pos_cfg.get("max_open_positions_per_symbol"), 1)
            symbol_open_count = 1 if self._has_open_position(session.id, symbol) else 0
            if symbol_open_count >= max_per_symbol:
                return self._block(session.id, error_codes.RISK_POSITION_SIZE_REJECTED)

            max_concurrent = self._as_int(pos_cfg.get("max_concurrent_positions"), 1)
            concurrent_open_count = self._count_open_positions(session.id)
            if concurrent_open_count >= max_concurrent:
                return self._block(session.id, error_codes.RISK_MAX_CONCURRENT_POSITIONS_REACHED)

        # 5) daily_loss_limit
        daily_limit_pct = self._as_float(risk_cfg.get("daily_loss_limit_pct"), 0.0)
        if daily_limit_pct > 0:
            baseline = self._as_float(
                session.performance_json.get("initial_capital")
                or self._as_dict(strategy_config.get("backtest")).get("initial_capital")
                or 1_000_000,
                1_000_000.0,
            )
            daily_loss = self._daily_loss.get(session.id, 0.0)
            if daily_loss >= baseline * daily_limit_pct:
                return self._block(session.id, error_codes.RISK_DAILY_LOSS_LIMIT_REACHED)

        # 6) strategy_drawdown_limit
        drawdown_limit_pct = self._as_float(risk_cfg.get("max_strategy_drawdown_pct"), 0.0)
        if drawdown_limit_pct > 0:
            drawdown = self._as_float(session.performance_json.get("max_drawdown_pct"), 0.0)
            if abs(drawdown) >= drawdown_limit_pct:
                return self._block(session.id, error_codes.RISK_MAX_DRAWDOWN_REACHED)

        # 7) kill_switch
        kill_enabled = bool(risk_cfg.get("kill_switch_enabled", False))
        current_state = self.get_risk_state(session.id)
        if kill_enabled and current_state == RiskState.KILL_SWITCHED:
            return self._block(session.id, error_codes.RISK_EMERGENCY_STOP_ACTIVE, risk_state=RiskState.KILL_SWITCHED)

        # 8) symbol_cooldown_reentry
        if signal_action == SignalAction.ENTER.value and bool(reentry_cfg.get("enabled", False)):
            reentry_state = self._reentry_states.get(session.id, {}).get(symbol, ReentryState.ELIGIBLE)
            if reentry_state in {ReentryState.COOLDOWN, ReentryState.WAIT_RESET, ReentryState.DISABLED}:
                return self._block(session.id, error_codes.EXEC_POSITION_STATE_INVALID)

        if signal_action == SignalAction.ENTER.value:
            self._mark_signal_seen(session.id, symbol, signal_action)
        self._risk_states[session.id] = RiskState.CLEAR
        return RiskCheckResult(passed=True, risk_state=RiskState.CLEAR.value, blocked_codes=[], warnings=[])

    def record_daily_loss(self, session_id: str, loss_amount: float) -> None:
        if loss_amount <= 0:
            return
        self._daily_loss[session_id] = self._daily_loss.get(session_id, 0.0) + loss_amount

    def register_position(self, session_id: str, symbol: str, state: PositionState) -> None:
        self._open_positions.setdefault(session_id, {})[symbol] = state

    def sync_open_positions(self, session_id: str, positions: list[Position]) -> None:
        self._open_positions[session_id] = {
            position.symbol: position.position_state
            for position in positions
            if position.position_state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}
        }

    def set_reentry_state(self, session_id: str, symbol: str, state: ReentryState) -> None:
        self._reentry_states.setdefault(session_id, {})[symbol] = state

    def activate_kill_switch(self, session_id: str) -> None:
        self._risk_states[session_id] = RiskState.KILL_SWITCHED

    def get_risk_state(self, session_id: str) -> RiskState:
        return self._risk_states.get(session_id, RiskState.CLEAR)

    def _is_action_allowed_for_mode(self, mode: ExecutionMode, signal_action: str) -> bool:
        if signal_action not in {SignalAction.ENTER.value, SignalAction.EXIT.value}:
            return False
        return mode in {ExecutionMode.BACKTEST, ExecutionMode.PAPER, ExecutionMode.LIVE}

    def _has_open_position(self, session_id: str, symbol: str) -> bool:
        state = self._open_positions.get(session_id, {}).get(symbol)
        return state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING}

    def _count_open_positions(self, session_id: str) -> int:
        states = self._open_positions.get(session_id, {}).values()
        return sum(1 for state in states if state in {PositionState.OPENING, PositionState.OPEN, PositionState.CLOSING})

    def _dedupe_key(self, session_id: str, symbol: str, signal_action: str) -> str:
        return f"{session_id}:{symbol}:{signal_action}"

    def _is_duplicate_signal(self, session_id: str, symbol: str, signal_action: str) -> bool:
        now = datetime.now(UTC)
        self._prune_signal_dedupe(now)
        dedupe_key = self._dedupe_key(session_id, symbol, signal_action)
        expires_at = self._signal_dedupe.get(dedupe_key)
        return expires_at is not None and expires_at > now

    def _mark_signal_seen(self, session_id: str, symbol: str, signal_action: str) -> None:
        dedupe_key = self._dedupe_key(session_id, symbol, signal_action)
        self._signal_dedupe[dedupe_key] = datetime.now(UTC) + timedelta(seconds=2)

    def _prune_signal_dedupe(self, now: datetime) -> None:
        expired = [key for key, expiry in self._signal_dedupe.items() if expiry <= now]
        for key in expired:
            del self._signal_dedupe[key]

    def _block(self, session_id: str, code: str, risk_state: RiskState = RiskState.BLOCKED) -> RiskCheckResult:
        self._risk_states[session_id] = risk_state
        logger.info("Risk guard blocked signal", extra={"error_code": code, "session_id": session_id, "risk_state": risk_state.value})
        return RiskCheckResult(
            passed=False,
            risk_state=risk_state.value,
            blocked_codes=[code],
            warnings=[],
        )

    def _as_dict(self, value: object) -> dict[str, object]:
        return cast(dict[str, object], value) if isinstance(value, dict) else {}

    def _as_int(self, value: object, fallback: int) -> int:
        return int(value) if isinstance(value, int | float) else fallback

    def _as_float(self, value: object, fallback: float) -> float:
        return float(value) if isinstance(value, int | float) else fallback
