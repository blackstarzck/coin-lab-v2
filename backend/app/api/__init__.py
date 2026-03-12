from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, cast

from ..core.trace import generate_trace_id, utc_now_iso


def serialize_for_api(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
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
