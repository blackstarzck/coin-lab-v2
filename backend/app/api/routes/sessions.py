from __future__ import annotations

from fastapi import APIRouter, Query

from .. import response_envelope
from ...application.container import get_container
from ...schemas.session import SessionCreate, SessionKillRequest, SessionReevaluateRequest, SessionStopRequest

router = APIRouter(prefix="/sessions")


@router.post("")
def create_session(payload: SessionCreate) -> dict[str, object]:
    session = get_container().session_service.create_session(payload)
    return response_envelope(session)


@router.get("")
def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    mode: str | None = None,
    status: str | None = None,
) -> dict[str, object]:
    rows, total = get_container().session_service.list_sessions(mode=mode, status=status, page=page, page_size=page_size)
    meta: dict[str, object] = {
        "page": int(page),
        "page_size": int(page_size),
        "total": int(total),
        "has_next": page * page_size < total,
    }
    return response_envelope(rows, meta)


@router.get("/{session_id}")
def get_session(session_id: str) -> dict[str, object]:
    return response_envelope(get_container().session_service.get_session(session_id))


@router.post("/{session_id}/stop")
def stop_session(session_id: str, payload: SessionStopRequest) -> dict[str, object]:
    result = get_container().session_service.stop_session(session_id, payload.reason)
    return response_envelope(result)


@router.post("/{session_id}/kill")
def kill_session(session_id: str, payload: SessionKillRequest) -> dict[str, object]:
    result = get_container().session_service.kill_session(session_id, payload.reason, payload.close_open_positions)
    return response_envelope(result)


@router.post("/{session_id}/reevaluate")
def reevaluate_session(session_id: str, payload: SessionReevaluateRequest) -> dict[str, object]:
    container = get_container()
    session = container.session_service.get_session(session_id)
    result = container.runtime_service.manual_reevaluate_session(session, payload.symbols)
    return response_envelope(result)


@router.get("/{session_id}/signals")
def get_signals(session_id: str, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, object]:
    rows = get_container().session_service.list_session_signals(session_id)[:limit]
    return response_envelope(rows)


@router.get("/{session_id}/positions")
def get_positions(session_id: str) -> dict[str, object]:
    rows = get_container().session_service.list_session_positions(session_id)
    return response_envelope(rows)


@router.get("/{session_id}/orders")
def get_orders(
    session_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    rows = get_container().session_service.list_session_orders(session_id)
    total = len(rows)
    start = (page - 1) * page_size
    data = rows[start : start + page_size]
    meta: dict[str, object] = {
        "page": int(page),
        "page_size": int(page_size),
        "total": int(total),
        "has_next": page * page_size < total,
    }
    return response_envelope(data, meta)


@router.get("/{session_id}/risk-events")
def get_risk_events(session_id: str, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, object]:
    rows = get_container().session_service.list_session_risk_events(session_id)[:limit]
    return response_envelope(rows)


@router.get("/{session_id}/performance")
def get_performance(session_id: str) -> dict[str, object]:
    return response_envelope(get_container().session_service.session_performance(session_id))
