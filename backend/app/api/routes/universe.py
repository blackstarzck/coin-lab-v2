from __future__ import annotations

from fastapi import APIRouter, Query

from .. import response_envelope
from ...application.container import get_container
from ...schemas.universe import UniversePreviewRequest

router = APIRouter(prefix="/universe")


@router.get("/current")
def current() -> dict[str, object]:
    return response_envelope(get_container().universe_service.get_current())


@router.get("/catalog")
def catalog(
    quote: str = Query(default="KRW", min_length=1, max_length=10),
    query: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, object]:
    return response_envelope(get_container().universe_service.catalog(quote=quote, query=query, limit=limit))


@router.post("/preview")
def preview(payload: UniversePreviewRequest) -> dict[str, object]:
    return response_envelope(get_container().universe_service.preview(payload.symbol_scope))
