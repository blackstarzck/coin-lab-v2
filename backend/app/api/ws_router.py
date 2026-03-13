from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket
from fastapi.encoders import jsonable_encoder
from starlette.websockets import WebSocketDisconnect

from app.application.container import get_container
from app.core.logging import get_logger
from app.core.trace import generate_trace_id, utc_now_iso

ws_router = APIRouter()
logger = get_logger(__name__)


@ws_router.websocket("/ws/monitoring")
async def monitoring_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    trace_id = generate_trace_id()
    stream_service = get_container().stream_service
    queue = stream_service.register_monitoring_subscriber()
    try:
        try:
            await websocket.send_json(
                jsonable_encoder(
                {
                    "type": "monitoring_snapshot",
                    "trace_id": trace_id,
                    "timestamp": utc_now_iso(),
                    "data": stream_service.monitoring_snapshot(),
                }
                )
            )
        except WebSocketDisconnect:
            return
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=5.0)
                await websocket.send_json(jsonable_encoder({"trace_id": trace_id, **payload}))
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat", "trace_id": trace_id, "timestamp": utc_now_iso()})
    except WebSocketDisconnect:
        return
    finally:
        stream_service.unregister_monitoring_subscriber(queue)


@ws_router.websocket("/ws/charts/{symbol}")
async def charts_ws(websocket: WebSocket, symbol: str) -> None:
    await websocket.accept()
    trace_id = generate_trace_id()
    stream_service = get_container().stream_service
    timeframe = websocket.query_params.get("timeframe", "5m")
    limit = int(websocket.query_params.get("limit", "200"))
    queue = stream_service.register_chart_subscriber(symbol, timeframe)
    logger.info("Chart websocket accepted for %s (%s)", symbol, timeframe)
    try:
        await websocket.send_json(
            {
                "type": "chart_snapshot",
                "trace_id": trace_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "points": stream_service.chart_snapshot(symbol, timeframe, limit)["points"],
            }
        )
        while True:
            payload = await queue.get()
            await websocket.send_json({"trace_id": trace_id, **payload})
    except WebSocketDisconnect as exc:
        logger.info(
            "Chart websocket disconnected for %s (%s): code=%s reason=%s",
            symbol,
            timeframe,
            exc.code,
            getattr(exc, "reason", ""),
        )
        return
    finally:
        stream_service.unregister_chart_subscriber(symbol, timeframe, queue)


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
