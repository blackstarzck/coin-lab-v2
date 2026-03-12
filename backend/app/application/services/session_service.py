from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

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


def _now() -> datetime:
    return datetime.now(UTC)


class SessionService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

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
                message="Strategy version must be validated before starting a session",
                status_code=400,
                details={"strategy_version_id": data.strategy_version_id},
            )
        mode = ExecutionMode(str(data.mode))
        if mode == ExecutionMode.LIVE and (not data.confirm_live or not data.acknowledge_risk):
            raise CoinLabError(
                error_code=ErrorCode.LIVE_CONFIRMATION_REQUIRED,
                message="LIVE mode requires confirm_live and acknowledge_risk",
                status_code=400,
                details={"confirm_live": data.confirm_live, "acknowledge_risk": data.acknowledge_risk},
            )
        now = _now()
        session = Session(
            id=f"ses_{uuid4().hex[:12]}",
            mode=mode,
            status=SessionStatus.RUNNING,
            strategy_version_id=data.strategy_version_id,
            symbol_scope_json=data.symbol_scope,
            risk_overrides_json=data.risk_overrides,
            config_snapshot={},
            performance_json={},
            health_json={},
            trace_id=generate_trace_id(),
            started_at=now,
            ended_at=None,
            created_at=now,
            updated_at=now,
        )
        return self.store.create_session(session)

    def stop_session(self, session_id: str, reason: str) -> dict[str, str]:
        session = self.get_session(session_id)
        previous_status = session.status.value
        updated = self.store.update_session_status(session_id, SessionStatus.STOPPING.value)
        if updated is None:
            raise NotFoundError("Session not found", {"session_id": session_id})
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
        return {
            "session_id": session_id,
            "previous_status": previous_status,
            "current_status": updated.status.value,
            "reason": reason,
            "close_open_positions": close_open_positions,
        }

    def get_session_signals(self, session_id: str) -> list[Signal]:
        self.get_session(session_id)
        return self.store.list_session_signals(session_id)

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
