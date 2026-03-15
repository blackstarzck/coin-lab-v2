from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from ...core.config import Settings
from ...core.error_codes import ErrorCode
from ...core.exceptions import CoinLabError, NotFoundError
from ...core.trace import generate_trace_id
from ...domain.entities.session import (
    ExecutionMode,
    Order,
    Position,
    RiskEvent,
    Session,
    SessionStatus,
    Signal,
)
from ...infrastructure.repositories.lab_store import LabStore
from ...schemas.session import SessionCreate
from .strategy_symbol_resolver import (
    resolve_strategy_symbols,
    strategy_static_symbols,
    strategy_universe_mode,
)
from .signal_explain_service import SignalExplainService

if TYPE_CHECKING:
    from .stream_service import StreamService


def _now() -> datetime:
    return datetime.now(UTC)


def _performance_defaults() -> dict[str, object]:
    return {
        "initial_capital": 1_000_000,
        "realized_pnl": 0.0,
        "realized_pnl_pct": 0.0,
        "unrealized_pnl": 0.0,
        "unrealized_pnl_pct": 0.0,
        "trade_count": 0,
        "win_rate_pct": 0.0,
        "max_drawdown_pct": 0.0,
    }


def _health_defaults() -> dict[str, object]:
    return {
        "connection_state": "CONNECTED",
        "snapshot_consistency": "HEALTHY",
        "late_event_count_5m": 0,
    }


class SessionService:
    def __init__(
        self,
        store: LabStore,
        settings: Settings,
        stream_service: StreamService | None = None,
        signal_explain_service: SignalExplainService | None = None,
    ) -> None:
        self.store = store
        self.settings = settings
        self.stream_service = stream_service
        self.signal_explain_service = signal_explain_service or SignalExplainService()

    def list_sessions(
        self,
        mode: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Session], int]:
        rows = self.store.list_sessions()
        if mode is not None:
            rows = [item for item in rows if item.mode.value == mode]
        if status is not None:
            rows = [item for item in rows if item.status.value == status]
        total = len(rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return rows[start:end], total

    def get_session(self, session_id: str) -> Session:
        session = self.store.get_session(session_id)
        if session is None:
            raise NotFoundError("Session not found", {"session_id": session_id})
        return session

    def create_session(self, data: SessionCreate) -> Session:
        strategy_version = self.store.get_strategy_version(data.strategy_version_id)
        if strategy_version is None:
            raise NotFoundError("Strategy version not found", {"strategy_version_id": data.strategy_version_id})
        if not strategy_version.is_validated:
            raise CoinLabError(
                error_code=ErrorCode.DSL_VALIDATION_FAILED,
                message="Validate the strategy version before starting a session.",
                status_code=400,
                details={"strategy_version_id": data.strategy_version_id},
            )

        mode = ExecutionMode(str(data.mode))
        if mode == ExecutionMode.LIVE and (not data.confirm_live or not data.acknowledge_risk):
            raise CoinLabError(
                error_code=ErrorCode.LIVE_CONFIRMATION_REQUIRED,
                message="confirm_live and acknowledge_risk are required in live mode.",
                status_code=400,
                details={"confirm_live": data.confirm_live, "acknowledge_risk": data.acknowledge_risk},
            )
        if mode == ExecutionMode.LIVE:
            self._validate_live_mode(data)

        symbol_scope = self._build_symbol_scope(data.symbol_scope, strategy_version.config_json)
        now = _now()
        session = Session(
            id=f"ses_{uuid4().hex[:12]}",
            mode=mode,
            status=SessionStatus.RUNNING,
            strategy_version_id=data.strategy_version_id,
            symbol_scope_json=symbol_scope,
            risk_overrides_json=data.risk_overrides,
            config_snapshot=strategy_version.config_json,
            performance_json=_performance_defaults(),
            health_json=_health_defaults(),
            trace_id=generate_trace_id(),
            started_at=now,
            ended_at=None,
            created_at=now,
            updated_at=now,
        )
        created = self.store.create_session(session)
        self._publish_monitoring_snapshot(force=True)
        return created

    def _validate_live_mode(self, data: SessionCreate) -> None:
        if not self.settings.live_trading_enabled:
            raise CoinLabError(
                error_code=ErrorCode.LIVE_MODE_SWITCH_BLOCKED,
                message="Live trading is disabled by configuration.",
                status_code=400,
                details={"live_trading_enabled": self.settings.live_trading_enabled},
            )
        if not self.settings.upbit_access_key or not self.settings.upbit_secret_key:
            raise CoinLabError(
                error_code=ErrorCode.LIVE_API_KEY_MISSING,
                message="Upbit API keys are required in live mode.",
                status_code=400,
                details={
                    "has_access_key": bool(self.settings.upbit_access_key),
                    "has_secret_key": bool(self.settings.upbit_secret_key),
                },
            )
        if self.settings.live_order_notional_krw < 5000:
            raise CoinLabError(
                error_code=ErrorCode.LIVE_MODE_SWITCH_BLOCKED,
                message="COIN_LAB_LIVE_ORDER_NOTIONAL_KRW must be at least 5000 in live mode.",
                status_code=400,
                details={"live_order_notional_krw": self.settings.live_order_notional_krw},
            )
        if self.settings.live_require_order_test and not data.order_test_passed:
            raise CoinLabError(
                error_code=ErrorCode.LIVE_MODE_SWITCH_BLOCKED,
                message="order_test_passed=true is required when COIN_LAB_LIVE_REQUIRE_ORDER_TEST is enabled.",
                status_code=400,
                details={
                    "live_require_order_test": self.settings.live_require_order_test,
                    "order_test_passed": data.order_test_passed,
                },
            )

    def _build_symbol_scope(self, requested_scope: dict[str, object], strategy_config: dict[str, object]) -> dict[str, object]:
        symbol_scope = dict(requested_scope)
        requested_symbols = symbol_scope.get("active_symbols")
        if not isinstance(requested_symbols, list) or not requested_symbols:
            requested_symbols = symbol_scope.get("symbols")

        resolved_symbols = resolve_strategy_symbols(
            requested_symbols,
            strategy_config,
            (
                str(item.get("symbol"))
                for item in self.store.get_current_universe()
                if isinstance(item, dict) and item.get("symbol")
            ),
        )

        if strategy_universe_mode(strategy_config) == "static" and "mode" not in symbol_scope:
            symbol_scope["mode"] = "static"

        configured_static_symbols = strategy_static_symbols(strategy_config)
        if configured_static_symbols and "symbols" not in symbol_scope:
            symbol_scope["symbols"] = configured_static_symbols

        max_symbols_raw = symbol_scope.get("max_symbols")
        max_symbols = max_symbols_raw if isinstance(max_symbols_raw, int) and max_symbols_raw > 0 else len(resolved_symbols)
        symbol_scope["active_symbols"] = resolved_symbols[:max_symbols]
        return symbol_scope

    def stop_session(self, session_id: str, reason: str) -> dict[str, str]:
        session = self.get_session(session_id)
        previous_status = session.status.value
        updated = self.store.update_session_status(session_id, SessionStatus.STOPPING.value)
        if updated is None:
            raise NotFoundError("Session not found", {"session_id": session_id})
        self._publish_monitoring_snapshot(force=True)
        return {
            "session_id": session_id,
            "previous_status": previous_status,
            "current_status": updated.status.value,
            "reason": reason,
        }

    def kill_session(self, session_id: str, reason: str, close_open_positions: bool = True) -> dict[str, str | bool]:
        session = self.get_session(session_id)
        previous_status = session.status.value
        updated = self.store.update_session_status(session_id, SessionStatus.STOPPING.value)
        if updated is None:
            raise NotFoundError("Session not found", {"session_id": session_id})
        self._publish_monitoring_snapshot(force=True)
        return {
            "session_id": session_id,
            "previous_status": previous_status,
            "current_status": updated.status.value,
            "reason": reason,
            "close_open_positions": close_open_positions,
        }

    def get_session_signals(self, session_id: str) -> list[Signal]:
        session = self.get_session(session_id)
        return [
            self.signal_explain_service.enrich_signal(signal, session.config_snapshot)
            for signal in self.store.list_session_signals(session_id)
        ]

    def get_session_positions(self, session_id: str) -> list[Position]:
        self.get_session(session_id)
        return self.store.list_session_positions(session_id)

    def get_session_orders(self, session_id: str) -> list[Order]:
        self.get_session(session_id)
        return self.store.list_session_orders(session_id)

    def get_session_risk_events(self, session_id: str) -> list[RiskEvent]:
        self.get_session(session_id)
        return self.store.list_session_risk_events(session_id)

    def get_session_performance(self, session_id: str) -> dict[str, object]:
        return self.get_session(session_id).performance_json

    def list_session_signals(self, session_id: str) -> list[Signal]:
        return self.get_session_signals(session_id)

    def list_session_positions(self, session_id: str) -> list[Position]:
        return self.get_session_positions(session_id)

    def list_session_orders(self, session_id: str) -> list[Order]:
        return self.get_session_orders(session_id)

    def list_session_risk_events(self, session_id: str) -> list[RiskEvent]:
        return self.get_session_risk_events(session_id)

    def session_performance(self, session_id: str) -> dict[str, object]:
        return self.get_session_performance(session_id)

    def _publish_monitoring_snapshot(self, force: bool = False) -> None:
        if self.stream_service is not None:
            self.stream_service.publish_monitoring_snapshot(force=force)
