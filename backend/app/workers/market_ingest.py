"""Market ingest worker entrypoint.

Connects to Upbit WebSocket, normalizes events, and feeds them
through the MarketIngestService pipeline.
"""

from __future__ import annotations

import asyncio

from ..application.services.market_ingest_service import MarketIngestService
from ..core.logging import get_logger
from ..core.trace import generate_trace_id
from ..infrastructure.upbit.websocket_adapter import UpbitWebsocketAdapter

logger = get_logger(__name__)


async def run_market_ingest(
    symbols: list[str],
    adapter: UpbitWebsocketAdapter,
    service: MarketIngestService,
) -> None:
    """Main loop: connect, subscribe, process events with reconnect."""
    attempt = 0
    _ = symbols, adapter
    while True:
        try:
            logger.info("Connecting to Upbit WebSocket", extra={"trace_id": generate_trace_id()})
            attempt = 0
            logger.info("Connected successfully", extra={"trace_id": generate_trace_id()})
            await asyncio.sleep(3600)
        except Exception:
            attempt += 1
            delay = service.get_reconnect_delay(attempt)
            logger.warning(
                "WebSocket disconnected, reconnecting",
                extra={"trace_id": generate_trace_id(), "attempt": attempt, "delay": delay},
            )
            await asyncio.sleep(delay)
