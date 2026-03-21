from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
import threading
from typing import Any, Iterable

from ...domain.entities.market import MarketSnapshot
from ...infrastructure.repositories.lab_store import LabStore
from .monitoring_service import MonitoringService


def _queue_put_latest(queue: asyncio.Queue[dict[str, object]], payload: dict[str, object]) -> None:
    if queue.full():
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
    queue.put_nowait(payload)


def _dispatch_queue(
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[dict[str, object]],
    payload: dict[str, object],
) -> None:
    if loop.is_closed():
        return
    try:
        loop.call_soon_threadsafe(_queue_put_latest, queue, payload)
    except RuntimeError:
        pass


def _normalize_symbols(symbols: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        cleaned = str(symbol).strip()
        if not cleaned or cleaned in seen:
            continue
        normalized.append(cleaned)
        seen.add(cleaned)
    return tuple(normalized)


class StreamService:
    def __init__(self, store: LabStore, monitoring_service: MonitoringService | None = None) -> None:
        self.store = store
        self._monitoring_service = monitoring_service or MonitoringService(store)
        self._lock = threading.RLock()
        self._chart_history: dict[tuple[str, str], deque[dict[str, object]]] = defaultdict(lambda: deque(maxlen=400))
        self._latest_prices: dict[str, dict[str, object | None]] = {}
        self._monitoring_subscribers: dict[asyncio.Queue[dict[str, object]], asyncio.AbstractEventLoop] = {}
        self._chart_subscribers: dict[
            tuple[str, str],
            dict[asyncio.Queue[dict[str, object]], asyncio.AbstractEventLoop],
        ] = defaultdict(dict)
        self._price_subscribers: dict[
            str,
            dict[asyncio.Queue[dict[str, object]], asyncio.AbstractEventLoop],
        ] = defaultdict(dict)
        self.connection_state: str = "DISCONNECTED"
        self.reconnect_count_1h: int = 0
        self._last_monitoring_publish_at: datetime | None = None

    def set_runtime_state(self, connection_state: str, reconnect_count: int) -> None:
        with self._lock:
            self.connection_state = connection_state
            self.reconnect_count_1h = reconnect_count
        self.publish_monitoring_snapshot(force=True)

    def monitoring_snapshot(self) -> dict[str, object]:
        return self._monitoring_service.get_summary()

    def chart_snapshot(self, symbol: str, timeframe: str, limit: int = 200) -> dict[str, object]:
        with self._lock:
            history = list(self._chart_history.get((symbol, timeframe), deque()))
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "points": history[-limit:],
        }

    def price_snapshot(self, symbols: Iterable[str]) -> dict[str, object]:
        requested_symbols = _normalize_symbols(symbols)
        with self._lock:
            items = [
                {
                    "symbol": symbol,
                    "price": self._latest_prices.get(symbol, {}).get("price"),
                    "timestamp": self._latest_prices.get(symbol, {}).get("timestamp"),
                    "buy_entry_rate_pct": self._latest_prices.get(symbol, {}).get("buy_entry_rate_pct"),
                    "sell_entry_rate_pct": self._latest_prices.get(symbol, {}).get("sell_entry_rate_pct"),
                    "entry_rate_window_sec": self._latest_prices.get(symbol, {}).get("entry_rate_window_sec"),
                }
                for symbol in requested_symbols
            ]
        return {"symbols": items}

    def record_snapshot(self, snapshot: MarketSnapshot) -> None:
        if snapshot.latest_price is not None:
            price_timestamp = snapshot.snapshot_time.astimezone(UTC).isoformat().replace("+00:00", "Z")
            with self._lock:
                self._latest_prices[snapshot.symbol] = {
                    "price": snapshot.latest_price,
                    "timestamp": price_timestamp,
                    "buy_entry_rate_pct": snapshot.buy_entry_rate_pct,
                    "sell_entry_rate_pct": snapshot.sell_entry_rate_pct,
                    "entry_rate_window_sec": snapshot.entry_rate_window_sec,
                }
                price_subscribers = list(self._price_subscribers.get(snapshot.symbol, {}).items())

            price_payload = {
                "type": "price_update",
                "symbol": snapshot.symbol,
                "price": snapshot.latest_price,
                "timestamp": price_timestamp,
                "buy_entry_rate_pct": snapshot.buy_entry_rate_pct,
                "sell_entry_rate_pct": snapshot.sell_entry_rate_pct,
                "entry_rate_window_sec": snapshot.entry_rate_window_sec,
            }
            for queue, loop in price_subscribers:
                _dispatch_queue(loop, queue, price_payload)

        for timeframe, candle in snapshot.candles.items():
            point = {
                "time": candle.candle_start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            history_key = (snapshot.symbol, timeframe)
            with self._lock:
                history = self._chart_history[history_key]
                if history and str(history[-1]["time"]) == point["time"]:
                    history[-1] = point
                else:
                    history.append(point)
                subscribers = list(self._chart_subscribers.get(history_key, {}).items())

            payload = {
                "type": "chart_point",
                "symbol": snapshot.symbol,
                "timeframe": timeframe,
                "point": point,
            }
            for queue, loop in subscribers:
                _dispatch_queue(loop, queue, payload)

    def publish_monitoring_snapshot(self, force: bool = False) -> None:
        now = datetime.now(UTC)
        with self._lock:
            if (
                not force
                and self._last_monitoring_publish_at is not None
                and now - self._last_monitoring_publish_at < timedelta(seconds=1)
            ):
                return
            self._last_monitoring_publish_at = now
            subscribers = list(self._monitoring_subscribers.items())
        payload = {
            "type": "monitoring_snapshot",
            "timestamp": now.isoformat().replace("+00:00", "Z"),
            "data": self.monitoring_snapshot(),
        }
        for queue, loop in subscribers:
            _dispatch_queue(loop, queue, payload)

    def register_monitoring_subscriber(self) -> asyncio.Queue[dict[str, object]]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=10)
        with self._lock:
            self._monitoring_subscribers[queue] = loop
        return queue

    def unregister_monitoring_subscriber(self, queue: asyncio.Queue[dict[str, object]]) -> None:
        with self._lock:
            self._monitoring_subscribers.pop(queue, None)

    def register_chart_subscriber(self, symbol: str, timeframe: str) -> asyncio.Queue[dict[str, object]]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=100)
        with self._lock:
            self._chart_subscribers[(symbol, timeframe)][queue] = loop
        return queue

    def unregister_chart_subscriber(self, symbol: str, timeframe: str, queue: asyncio.Queue[dict[str, object]]) -> None:
        key = (symbol, timeframe)
        with self._lock:
            subscribers = self._chart_subscribers.get(key)
            if not subscribers:
                return
            subscribers.pop(queue, None)
            if not subscribers:
                self._chart_subscribers.pop(key, None)

    def register_price_subscriber(
        self,
        symbols: Iterable[str],
    ) -> tuple[tuple[str, ...], asyncio.Queue[dict[str, object]]]:
        normalized_symbols = _normalize_symbols(symbols)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue(maxsize=max(10, len(normalized_symbols) * 4))
        with self._lock:
            for symbol in normalized_symbols:
                self._price_subscribers[symbol][queue] = loop
        return normalized_symbols, queue

    def unregister_price_subscriber(
        self,
        symbols: Iterable[str],
        queue: asyncio.Queue[dict[str, object]],
    ) -> None:
        normalized_symbols = _normalize_symbols(symbols)
        with self._lock:
            for symbol in normalized_symbols:
                subscribers = self._price_subscribers.get(symbol)
                if not subscribers:
                    continue
                subscribers.pop(queue, None)
                if not subscribers:
                    self._price_subscribers.pop(symbol, None)

    def backtest_stream_event(self, run_id: str) -> dict[str, object]:
        return {"run_id": run_id, "status": "COMPLETED", "progress": 100}

    def warm_chart_history(self, symbol: str, timeframe: str, points: list[dict[str, Any]]) -> None:
        with self._lock:
            history = self._chart_history[(symbol, timeframe)]
            history.clear()
            history.extend(points)
