from __future__ import annotations

from fastapi import APIRouter

from .. import response_envelope
from ...application.container import get_container

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    return response_envelope(get_container().health_service.health())


@router.get("/runtime/status")
def runtime_status() -> dict[str, object]:
    return response_envelope(get_container().runtime_service.status())


@router.post("/runtime/start")
def runtime_start() -> dict[str, object]:
    return response_envelope(get_container().runtime_service.start())


@router.post("/runtime/stop")
def runtime_stop() -> dict[str, object]:
    return response_envelope(get_container().runtime_service.stop())


@router.get("/metadata/indicators")
def metadata_indicators() -> dict[str, object]:
    return response_envelope(get_container().health_service.metadata_indicators())


@router.get("/metadata/strategy-operators")
def metadata_operators() -> dict[str, object]:
    return response_envelope(get_container().health_service.metadata_strategy_operators())


@router.get("/metadata/timeframes")
def metadata_timeframes() -> dict[str, object]:
    return response_envelope(get_container().health_service.metadata_timeframes())


@router.get("/metadata/markets")
def metadata_markets() -> dict[str, object]:
    return response_envelope(get_container().health_service.metadata_markets())
