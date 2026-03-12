from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, cast

from ..domain.entities.session import Session as SessionEntity
from ..core.trace import generate_trace_id, utc_now_iso


def serialize_for_api(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, SessionEntity):
        return {
            "id": value.id,
            "mode": serialize_for_api(value.mode),
            "status": serialize_for_api(value.status),
            "strategy_version_id": value.strategy_version_id,
            "symbol_scope": serialize_for_api(value.symbol_scope_json),
            "risk_overrides": serialize_for_api(value.risk_overrides_json),
            "performance": serialize_for_api(value.performance_json),
            "health": serialize_for_api(value.health_json),
            "started_at": serialize_for_api(value.started_at),
            "ended_at": serialize_for_api(value.ended_at),
            "created_at": serialize_for_api(value.created_at),
            "updated_at": serialize_for_api(value.updated_at),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return serialize_for_api(asdict(cast(Any, value)))
    if isinstance(value, dict):
        return {str(key): serialize_for_api(item) for key, item in value.items()}
    if isinstance(value, list):
        return [serialize_for_api(item) for item in value]
    return value


def response_envelope(
    data: object | list[object] | dict[str, object] | None,
    meta: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "success": True,
        "data": serialize_for_api(data),
        "trace_id": generate_trace_id(),
        "timestamp": utc_now_iso(),
    }
    if meta is not None:
        payload["meta"] = dict(meta)
    return payload
