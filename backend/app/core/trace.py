from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def generate_trace_id() -> str:
    return f"trc_{uuid4().hex}"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
