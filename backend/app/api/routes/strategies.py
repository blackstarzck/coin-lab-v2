from __future__ import annotations

from fastapi import APIRouter, Query

from .. import response_envelope
from ...application.container import get_container
from ...schemas.strategy import DraftValidateRequest, StrategyCreate, StrategyUpdate, StrategyVersionCreate, ValidateRequest

router = APIRouter(prefix="/strategies")
version_router = APIRouter()


@router.post("")
def create_strategy(payload: StrategyCreate) -> dict[str, object]:
    strategy = get_container().strategy_service.create_strategy(payload)
    return response_envelope(strategy)


@router.get("")
def list_strategies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    is_active: bool | None = None,
    label: str | None = None,
) -> dict[str, object]:
    rows, total = get_container().strategy_service.list_strategies(
        is_active=is_active,
        label=label,
        page=page,
        page_size=page_size,
    )
    meta: dict[str, object] = {
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": page * page_size < total,
    }
    return response_envelope(rows, meta)


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.get_strategy(strategy_id))


@router.patch("/{strategy_id}")
def update_strategy(strategy_id: str, payload: StrategyUpdate) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.update_strategy(strategy_id, payload))


@router.get("/{strategy_id}/versions")
def list_versions(strategy_id: str) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.list_strategy_versions(strategy_id))


@router.post("/{strategy_id}/versions")
def create_version(strategy_id: str, payload: StrategyVersionCreate) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.create_strategy_version(strategy_id, payload))


@router.post("/validate-draft")
def validate_draft(payload: DraftValidateRequest) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.validate_draft(payload.config_json, payload.strict))


@version_router.get("/strategy-versions/{version_id}")
def get_version(version_id: str) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.get_strategy_version(version_id))


@version_router.post("/strategy-versions/{version_id}/validate")
def validate_version(version_id: str, payload: ValidateRequest) -> dict[str, object]:
    return response_envelope(get_container().strategy_service.validate_strategy_version(version_id, payload.strict))
