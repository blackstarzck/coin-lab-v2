from __future__ import annotations

from fastapi import APIRouter, WebSocket

from app.core.trace import generate_trace_id, utc_now_iso

ws_router = APIRouter()


@ws_router.websocket("/ws/monitoring")
async def monitoring_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    trace_id = generate_trace_id()
    await websocket.send_json(
        {
            "type": "monitoring_snapshot",
            "trace_id": trace_id,
            "timestamp": utc_now_iso(),
            "data": {
                "status_bar": {
                    "running_session_count": 0,
                    "paper_session_count": 0,
                    "live_session_count": 0,
                    "failed_session_count": 0,
                    "degraded_session_count": 0,
                    "active_symbol_count": 4,
                }
            },
        }
    )
    await websocket.send_json({"type": "heartbeat", "trace_id": trace_id, "timestamp": utc_now_iso()})
    await websocket.close()


@ws_router.websocket("/ws/charts/{symbol}")
async def charts_ws(websocket: WebSocket, symbol: str) -> None:
    await websocket.accept()
    trace_id = generate_trace_id()
    timeframe = websocket.query_params.get("timeframe", "5m")
    await websocket.send_json(
        {
            "type": "chart_snapshot",
            "trace_id": trace_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "points": [
                {
                    "time": "2026-03-11T15:55:00Z",
                    "open": 143120000,
                    "high": 143500000,
                    "low": 143000000,
                    "close": 143420000,
                    "volume": 12.34,
                }
            ],
        }
    )
    await websocket.send_json(
        {
            "type": "chart_point",
            "trace_id": trace_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "point": {
                "time": "2026-03-11T16:00:00Z",
                "open": 143420000,
                "high": 143700000,
                "low": 143300000,
                "close": 143520000,
                "volume": 15.21,
            },
        }
    )
    await websocket.close()


@ws_router.websocket("/ws/backtests/{run_id}")
async def backtests_ws(websocket: WebSocket, run_id: str) -> None:
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "backtest_update",
            "trace_id": generate_trace_id(),
            "timestamp": utc_now_iso(),
            "run_id": run_id,
            "data": {"status": "COMPLETED", "progress": 100},
        }
    )
    await websocket.close()
