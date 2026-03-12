from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
import threading
from typing import Any

from ...domain.entities.market import MarketSnapshot
from ...infrastructure.repositories.lab_store import LabStore


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


class StreamService:
    def __init__(self, store: LabStore) -> None:
        self.store = store
        self._lock = threading.RLock()
        self._chart_history: dict[tuple[str, str], deque[dict[str, object]]] = defaultdict(lambda: deque(maxlen=400))
        self._monitoring_subscribers: dict[asyncio.Queue[dict[str, object]], asyncio.AbstractEventLoop] = {}
        self._chart_subscribers: dict[
            tuple[str, str],
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
        sessions = self.store.list_sessions()
        with self._lock:
            connection_state = self.connection_state
            reconnect_count_1h = self.reconnect_count_1h
        running = [session for session in sessions if session.status.value == "RUNNING"]
        paper = [session for session in running if session.mode.value == "PAPER"]
        live = [session for session in running if session.mode.value == "LIVE"]
        failed = [session for session in sessions if session.status.value == "FAILED"]
        degraded = [
            session
            for session in running
            if str(session.health_json.get("connection_state", connection_state)).upper()
            in {"DEGRADED", "DISCONNECTED", "RECONNECTING"}
            or str(session.health_json.get("snapshot_consistency", "HEALTHY")).upper() != "HEALTHY"
        ]
        active_symbols = {
            str(symbol)
            for session in running
            for symbol in session.symbol_scope_json.get("active_symbols", [])
            if isinstance(symbol, str)
        }
        return {
            "status_bar": {
                "running_session_count": len(running),
                "paper_session_count": len(paper),
                "live_session_count": len(live),
                "failed_session_count": len(failed),
                "degraded_session_count": len(degraded),
                "active_symbol_count": len(active_symbols),
            },
            "runtime": {
                "connection_state": connection_state,
                "reconnect_count_1h": reconnect_count_1h,
            },
        }

    def chart_snapshot(self, symbol: str, timeframe: str, limit: int = 200) -> dict[str, object]:
        with self._lock:
            history = list(self._chart_history.get((symbol, timeframe), deque()))
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "points": history[-limit:],
        }

    def record_snapshot(self, snapshot: MarketSnapshot) -> None:
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

        self.publish_monitoring_snapshot()

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

    def backtest_stream_event(self, run_id: str) -> dict[str, object]:
        return {"run_id": run_id, "status": "COMPLETED", "progress": 100}

    def warm_chart_history(self, symbol: str, timeframe: str, points: list[dict[str, Any]]) -> None:
        with self._lock:
            history = self._chart_history[(symbol, timeframe)]
            history.clear()
            history.extend(points)
