from __future__ import annotations

from fastapi import APIRouter, Query

from .. import response_envelope
from ...application.container import get_container

router = APIRouter(prefix="/logs")


def _query_channel(channel: str, session_id: str | None, limit: int) -> dict[str, object]:
    data = get_container().log_service.list_channel_logs(channel, session_id, limit)
    return response_envelope(data)


@router.get("/system")
def system_logs(session_id: str | None = None, limit: int = Query(default=50, ge=1, le=500)) -> dict[str, object]:
    return _query_channel("system", session_id, limit)


@router.get("/strategy-execution")
def strategy_execution_logs(
    session_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    return _query_channel("strategy-execution", session_id, limit)


@router.get("/order-simulation")
def order_simulation_logs(
    session_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    return _query_channel("order-simulation", session_id, limit)


@router.get("/risk-control")
def risk_control_logs(
    session_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    return _query_channel("risk-control", session_id, limit)


@router.get("/documents")
def document_logs(
    session_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    return _query_channel("documents", session_id, limit)
