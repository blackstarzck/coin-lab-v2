from __future__ import annotations

from fastapi import APIRouter

from .. import response_envelope
from ...application.container import get_container
from ...schemas.universe import UniversePreviewRequest

router = APIRouter(prefix="/universe")


@router.get("/current")
def current() -> dict[str, object]:
    return response_envelope(get_container().universe_service.get_current())


@router.post("/preview")
def preview(payload: UniversePreviewRequest) -> dict[str, object]:
    return response_envelope(get_container().universe_service.preview(payload.symbol_scope))
