from __future__ import annotations

from fastapi import APIRouter, Query

from .. import response_envelope
from ...application.container import get_container
from ...schemas.backtest import BacktestCompareRequest, BacktestRunRequest

router = APIRouter(prefix="/backtests")


@router.post("/run")
def create_run(payload: BacktestRunRequest) -> dict[str, object]:
    return response_envelope(get_container().backtest_service.run_backtest(payload))


@router.get("")
def list_runs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    rows, total = get_container().backtest_service.list_backtests(page=page, page_size=page_size)
    meta: dict[str, object] = {
        "page": int(page),
        "page_size": int(page_size),
        "total": int(total),
        "has_next": page * page_size < total,
    }
    return response_envelope(rows, meta)


@router.get("/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    return response_envelope(get_container().backtest_service.get_backtest(run_id))


@router.get("/{run_id}/trades")
def get_trades(
    run_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict[str, object]:
    rows = get_container().backtest_service.list_backtest_trades(run_id)
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


@router.get("/{run_id}/performance")
def get_performance(run_id: str) -> dict[str, object]:
    return response_envelope(get_container().backtest_service.get_performance(run_id))


@router.get("/{run_id}/equity-curve")
def get_equity_curve(run_id: str) -> dict[str, object]:
    return response_envelope(get_container().backtest_service.get_equity_curve(run_id))


@router.post("/{run_id}/compare")
def compare(run_id: str, payload: BacktestCompareRequest) -> dict[str, object]:
    return response_envelope(get_container().backtest_service.compare_runs(run_id, payload.against_run_ids))
