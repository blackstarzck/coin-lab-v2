from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast

from ...core import error_codes
from ...core.logging import get_logger
from ...domain.entities.market import CandleState, ConnectionState, EventType, MarketSnapshot, NormalizedEvent

logger = get_logger(__name__)


@dataclass(slots=True)
class _TickBuffer:
    events: list[NormalizedEvent]
    first_received_at: datetime


class MarketIngestService:
    BUFFER_MAX_AGE_MS: int = 250
    BUFFER_MAX_SIZE: int = 200
    REORDER_WINDOW_SECONDS: int = 2

    DEDUPE_TTL_TICK: timedelta = timedelta(minutes=10)
    DEDUPE_TTL_CANDLE: timedelta = timedelta(hours=48)
    DEDUPE_TTL_SYSTEM: timedelta = timedelta(hours=24)

    BACKOFF_SEQUENCE: tuple[int, ...] = (1, 2, 5, 10, 20, 30)
    JITTER_RATIO: float = 0.2

    SNAPSHOT_STALE_THRESHOLDS: dict[str, int] = {
        "tick": 2,
        "1m": 70,
        "5m": 360,
        "15m": 960,
    }

    DEFAULT_BASE_SYMBOLS: list[str] = [
        "KRW-BTC",
        "KRW-ETH",
        "KRW-XRP",
        "KRW-SOL",
        "KRW-ADA",
        "KRW-DOGE",
        "KRW-AVAX",
        "KRW-LINK",
    ]

    def __init__(self) -> None:
        self.connection_state: ConnectionState = ConnectionState.CONNECTED
        self._dedupe_seen: dict[str, datetime] = {}
        self._latest_event_time: dict[str, datetime] = {}
        self._tick_buffers: dict[str, _TickBuffer] = {}
        self._latest_price: dict[str, float] = {}
        self._volume_24h: dict[str, float] = {}
        self._candles: dict[str, dict[str, CandleState]] = {}
        self._snapshots: dict[str, MarketSnapshot] = {}

    @property
    def snapshots(self) -> dict[str, MarketSnapshot]:
        return self._snapshots

    def buffer_tick(self, event: NormalizedEvent) -> list[NormalizedEvent] | None:
        if event.event_type != EventType.TRADE_TICK:
            return None

        symbol = event.symbol
        buffer = self._tick_buffers.get(symbol)
        if buffer is None:
            self._tick_buffers[symbol] = _TickBuffer(events=[event], first_received_at=event.received_at)
            return None

        buffer.events.append(event)
        age_ms = (event.received_at - buffer.first_received_at).total_seconds() * 1000
        if len(buffer.events) >= self.BUFFER_MAX_SIZE or age_ms >= self.BUFFER_MAX_AGE_MS:
            return self.flush_buffer(symbol)
        return None

    def flush_buffer(self, symbol: str) -> list[NormalizedEvent]:
        buffer = self._tick_buffers.get(symbol)
        if buffer is None:
            return []
        events = sorted(buffer.events, key=lambda item: item.event_time)
        del self._tick_buffers[symbol]
        return events

    def is_duplicate(self, event: NormalizedEvent) -> bool:
        now = event.received_at
        self._prune_dedupe(now)
        expires_at = self._dedupe_seen.get(event.dedupe_key)
        if expires_at is not None and expires_at > now:
            logger.debug(
                "Duplicate event dropped",
                extra={"error_code": error_codes.EVT_DUPLICATE_DROPPED, "dedupe_key": event.dedupe_key},
            )
            return True

        self._dedupe_seen[event.dedupe_key] = now + self._ttl_for_event(event)
        return False

    def check_ordering(self, event: NormalizedEvent) -> bool:
        latest = self._latest_event_time.get(event.symbol)
        if latest is None:
            self._latest_event_time[event.symbol] = event.event_time
            return True

        reorder_window = timedelta(seconds=self.REORDER_WINDOW_SECONDS)
        if event.event_time < latest - reorder_window:
            logger.debug(
                "Out-of-order event dropped",
                extra={
                    "error_code": error_codes.EVT_OUT_OF_ORDER_DROPPED,
                    "symbol": event.symbol,
                    "event_time": event.event_time.isoformat(),
                    "latest_time": latest.isoformat(),
                },
            )
            return False

        if event.event_time > latest:
            self._latest_event_time[event.symbol] = event.event_time
        return True

    def is_snapshot_stale(self, snapshot_time: datetime, basis: str) -> bool:
        threshold = self.SNAPSHOT_STALE_THRESHOLDS.get(basis, self.SNAPSHOT_STALE_THRESHOLDS["tick"])
        stale = (datetime.now(UTC) - snapshot_time).total_seconds() > threshold
        if stale:
            logger.debug(
                "Snapshot is stale",
                extra={"error_code": error_codes.EXEC_SNAPSHOT_STALE, "basis": basis},
            )
        return stale

    def get_reconnect_delay(self, attempt: int) -> float:
        index = max(0, min(attempt - 1, len(self.BACKOFF_SEQUENCE) - 1))
        base = float(self.BACKOFF_SEQUENCE[index])
        jitter = random.uniform(1 - self.JITTER_RATIO, 1 + self.JITTER_RATIO)
        return base * jitter

    def create_snapshot(self, symbol: str) -> MarketSnapshot:
        now = datetime.now(UTC)
        candles = dict(self._candles.get(symbol, {}))
        snapshot = MarketSnapshot(
            symbol=symbol,
            latest_price=self._latest_price.get(symbol),
            candles=candles,
            volume_24h=self._volume_24h.get(symbol),
            snapshot_time=now,
            is_stale=self.is_snapshot_stale(now, "tick"),
            connection_state=self.connection_state,
        )
        self._snapshots[symbol] = snapshot
        return snapshot

    def refresh_candidate_pool(self, config: dict[str, object]) -> list[str]:
        universe_cfg_raw = config.get("universe")
        universe_cfg: dict[str, object] = cast(dict[str, object], universe_cfg_raw) if isinstance(universe_cfg_raw, dict) else {}

        max_symbols_raw = universe_cfg.get("max_symbols", 4)
        max_symbols = max_symbols_raw if isinstance(max_symbols_raw, int) and max_symbols_raw > 0 else 4

        sources_raw: object = universe_cfg.get("sources")
        if isinstance(sources_raw, list):
            source_items = cast(list[object], sources_raw)
            sources: list[str] = [item for item in source_items if isinstance(item, str)]
        else:
            sources = []
        if not sources:
            sources = ["base_market", "watchlist"]

        strategy_raw: object = universe_cfg.get("strategy_compatibility")
        if isinstance(strategy_raw, list):
            strategy_items = cast(list[object], strategy_raw)
            strategy_filter: list[str] = [item for item in strategy_items if isinstance(item, str)]
        else:
            strategy_filter = []

        base_market = list(self.DEFAULT_BASE_SYMBOLS)
        turnover_ranked = ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-DOGE"]
        surge_symbols = ["KRW-SOL", "KRW-DOGE", "KRW-AVAX"]
        watchlist = ["KRW-ETH", "KRW-LINK", "KRW-XRP"]

        candidates: list[str] = []
        if "base_market" in sources:
            candidates.extend(base_market)
        if "turnover" in sources:
            candidates.extend(turnover_ranked)
        if "surge" in sources or "volume_spike" in sources:
            candidates.extend(surge_symbols)
        if "watchlist" in sources:
            candidates.extend(watchlist)

        deduped: list[str] = []
        seen: set[str] = set()
        for symbol in candidates:
            if symbol in seen:
                continue
            seen.add(symbol)
            deduped.append(symbol)

        if strategy_filter:
            compatible = [symbol for symbol in deduped if any(token in symbol for token in strategy_filter)]
            if compatible:
                deduped = compatible

        return deduped[:max_symbols]

    def process_event(self, event: NormalizedEvent) -> dict[str, object]:
        if self.is_duplicate(event):
            return {"accepted": False, "event_type": event.event_type.value, "reason": error_codes.EVT_DUPLICATE_DROPPED}

        if not self.check_ordering(event):
            return {"accepted": False, "event_type": event.event_type.value, "reason": error_codes.EVT_OUT_OF_ORDER_DROPPED}

        if event.event_type == EventType.SYSTEM_CONNECTION:
            self._handle_connection_event(event)
            if self.connection_state in {ConnectionState.DISCONNECTED, ConnectionState.RECONNECTING}:
                _ = self.flush_buffer(event.symbol)
            _ = self.create_snapshot(event.symbol)
            return {"accepted": True, "event_type": event.event_type.value, "reason": None}

        batch = self.buffer_tick(event)
        if batch:
            self._apply_events(batch)
            _ = self.create_snapshot(event.symbol)
            return {"accepted": True, "event_type": event.event_type.value, "reason": "tick_batch_flushed"}

        if event.event_type != EventType.TRADE_TICK:
            self._apply_event(event)
            _ = self.create_snapshot(event.symbol)
            return {"accepted": True, "event_type": event.event_type.value, "reason": None}

        return {"accepted": True, "event_type": event.event_type.value, "reason": "tick_buffered"}

    def ingest_event(self, event: dict[str, object]) -> dict[str, object]:
        event_type_raw = event.get("event_type")
        event_type_name = event_type_raw if isinstance(event_type_raw, str) else EventType.TRADE_TICK.value
        try:
            event_type = EventType(event_type_name)
        except ValueError:
            return {"accepted": False, "event_type": str(event_type_name), "reason": "unknown_event_type"}

        now = datetime.now(UTC)
        timeframe = event.get("timeframe")
        timeframe_value = timeframe if isinstance(timeframe, str) else None
        event_time_raw = event.get("event_time")
        event_time = event_time_raw if isinstance(event_time_raw, datetime) else now
        sequence_no_raw = event.get("sequence_no")
        sequence_no = sequence_no_raw if isinstance(sequence_no_raw, int) else None
        received_at_raw = event.get("received_at")
        received_at = received_at_raw if isinstance(received_at_raw, datetime) else now
        payload_raw = event.get("payload")
        payload = cast(dict[str, object], payload_raw) if isinstance(payload_raw, dict) else dict(event)

        normalized = NormalizedEvent(
            event_id=str(event.get("event_id", "evt_stub")),
            dedupe_key=str(event.get("dedupe_key", "stub:dedupe")),
            symbol=str(event.get("symbol", "KRW-BTC")),
            timeframe=timeframe_value,
            event_type=event_type,
            event_time=event_time,
            sequence_no=sequence_no,
            received_at=received_at,
            source=str(event.get("source", "unknown")),
            payload=payload,
            trace_id=str(event.get("trace_id", "trc_stub")),
        )
        return self.process_event(normalized)

    def _apply_events(self, events: list[NormalizedEvent]) -> None:
        for event in events:
            self._apply_event(event)

    def _apply_event(self, event: NormalizedEvent) -> None:
        symbol = event.symbol
        price = event.payload.get("trade_price") or event.payload.get("price")
        if isinstance(price, int | float):
            self._latest_price[symbol] = float(price)

        volume_24h = event.payload.get("acc_trade_volume_24h")
        if isinstance(volume_24h, int | float):
            self._volume_24h[symbol] = float(volume_24h)

        if event.event_type in {EventType.CANDLE_UPDATE, EventType.CANDLE_CLOSE}:
            timeframe = event.timeframe or "1m"
            open_price = self._as_float(event.payload.get("open"), self._latest_price.get(symbol, 0.0))
            high = self._as_float(event.payload.get("high"), open_price)
            low = self._as_float(event.payload.get("low"), open_price)
            close = self._as_float(event.payload.get("close"), self._latest_price.get(symbol, open_price))
            volume = self._as_float(event.payload.get("volume"), 0.0)
            candle = CandleState(
                symbol=symbol,
                timeframe=timeframe,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume,
                candle_start=event.event_time,
                is_closed=event.event_type == EventType.CANDLE_CLOSE,
                last_update=event.event_time,
            )
            self._candles.setdefault(symbol, {})[timeframe] = candle

    def _handle_connection_event(self, event: NormalizedEvent) -> None:
        state = event.payload.get("state")
        if isinstance(state, str):
            try:
                self.connection_state = ConnectionState(state)
            except ValueError:
                self.connection_state = ConnectionState.DEGRADED

    def _ttl_for_event(self, event: NormalizedEvent) -> timedelta:
        if event.event_type == EventType.TRADE_TICK:
            return self.DEDUPE_TTL_TICK
        if event.event_type in {EventType.CANDLE_UPDATE, EventType.CANDLE_CLOSE, EventType.ORDERBOOK_SNAPSHOT}:
            return self.DEDUPE_TTL_CANDLE
        return self.DEDUPE_TTL_SYSTEM

    def _prune_dedupe(self, now: datetime) -> None:
        expired = [key for key, expires_at in self._dedupe_seen.items() if expires_at <= now]
        for key in expired:
            del self._dedupe_seen[key]

    def _as_float(self, value: object, fallback: float) -> float:
        if isinstance(value, int | float):
            return float(value)
        return fallback
