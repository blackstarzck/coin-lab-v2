from __future__ import annotations

from fastapi import APIRouter

from .. import response_envelope
from ...application.container import get_container

router = APIRouter(prefix="/monitoring")


@router.get("/summary")
def summary() -> dict[str, object]:
    return response_envelope(get_container().monitoring_service.get_summary())
