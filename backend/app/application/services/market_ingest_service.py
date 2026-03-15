from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from typing import cast

from ...core import error_codes
from ...core.logging import get_logger
from ...domain.entities.market import (
    CandleState,
    ConnectionState,
    EvaluationTrigger,
    EventType,
    MarketSnapshot,
    NormalizedEvent,
)

logger = get_logger(__name__)


@dataclass(slots=True)
class _TickBuffer:
    events: list[NormalizedEvent]
    first_received_at: datetime


@dataclass(slots=True)
class _ApplyResult:
    updated_timeframes: set[str]
    closed_candles: dict[str, CandleState]


@dataclass(slots=True)
class _TradeFlowEntry:
    event_time: datetime
    side: str
    volume: float


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
    CANDLE_TIMEFRAMES: tuple[str, ...] = ("1m", "5m", "15m", "1h")
    CANDLE_HISTORY_LIMIT: int = 400
    ENTRY_RATE_WINDOW_SECONDS: int = 60
    ENTRY_RATE_WINDOW: timedelta = timedelta(seconds=ENTRY_RATE_WINDOW_SECONDS)

    def __init__(self) -> None:
        self.connection_state: ConnectionState = ConnectionState.CONNECTED
        self._dedupe_seen: dict[str, datetime] = {}
        self._latest_event_time: dict[str, datetime] = {}
        self._tick_buffers: dict[str, _TickBuffer] = {}
        self._latest_price: dict[str, float] = {}
        self._volume_24h: dict[str, float] = {}
        self._candles: dict[str, dict[str, CandleState]] = {}
        self._candle_history: dict[str, dict[str, deque[CandleState]]] = {}
        self._trade_flow: dict[str, deque[_TradeFlowEntry]] = {}
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

    def create_snapshot(
        self,
        symbol: str,
        *,
        snapshot_time: datetime | None = None,
        candle_overrides: dict[str, CandleState] | None = None,
        source_event_type: EventType | None = None,
        available_triggers: tuple[EvaluationTrigger, ...] = (),
        trigger_trace_ids: tuple[str, ...] = (),
        closed_timeframes: tuple[str, ...] = (),
        updated_timeframes: tuple[str, ...] = (),
        persist: bool = True,
    ) -> MarketSnapshot:
        current_time = snapshot_time or datetime.now(UTC)
        candles = dict(self._candles.get(symbol, {}))
        if candle_overrides:
            candles.update(candle_overrides)
        candle_history = self._history_for_snapshot(symbol, candles)
        freshness_basis = closed_timeframes[0] if closed_timeframes else "tick"
        buy_entry_rate_pct, sell_entry_rate_pct = self._entry_rate_snapshot(symbol, current_time)
        snapshot = MarketSnapshot(
            symbol=symbol,
            latest_price=self._latest_price.get(symbol),
            candles=candles,
            volume_24h=self._volume_24h.get(symbol),
            snapshot_time=current_time,
            buy_entry_rate_pct=buy_entry_rate_pct,
            sell_entry_rate_pct=sell_entry_rate_pct,
            entry_rate_window_sec=self.ENTRY_RATE_WINDOW_SECONDS,
            candle_history=candle_history,
            is_stale=self.is_snapshot_stale(current_time, freshness_basis),
            connection_state=self.connection_state,
            source_event_type=source_event_type,
            available_triggers=available_triggers,
            trigger_trace_ids=trigger_trace_ids,
            closed_timeframes=closed_timeframes,
            updated_timeframes=updated_timeframes,
        )
        if persist:
            self._snapshots[symbol] = snapshot
        return snapshot

    def build_manual_snapshot(self, symbol: str) -> MarketSnapshot | None:
        snapshot_time = self._latest_symbol_update_time(symbol)
        if snapshot_time is None:
            return None
        candles = self._candles.get(symbol, {})
        closed_timeframes = tuple(sorted(timeframe for timeframe, candle in candles.items() if candle.is_closed))
        updated_timeframes = tuple(sorted(candles))
        return self.create_snapshot(
            symbol,
            snapshot_time=snapshot_time,
            source_event_type=None,
            available_triggers=(EvaluationTrigger.ON_MANUAL_REEVALUATE,),
            trigger_trace_ids=(),
            closed_timeframes=closed_timeframes,
            updated_timeframes=updated_timeframes,
            persist=False,
        )

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
            sources = ["top_turnover", "watchlist"]

        strategy_raw: object = universe_cfg.get("strategy_compatibility")
        if isinstance(strategy_raw, list):
            strategy_items = cast(list[object], strategy_raw)
            strategy_filter: list[str] = [item for item in strategy_items if isinstance(item, str)]
        else:
            strategy_filter = []

        base_market = list(self.DEFAULT_BASE_SYMBOLS)
        turnover_ranked = ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-DOGE"]
        volume_ranked = ["KRW-BTC", "KRW-XRP", "KRW-DOGE", "KRW-SOL", "KRW-ADA"]
        surge_symbols = ["KRW-SOL", "KRW-DOGE", "KRW-AVAX"]
        drop_symbols = ["KRW-BTT", "KRW-STX", "KRW-BCH"]
        watchlist = ["KRW-ETH", "KRW-LINK", "KRW-XRP"]

        candidates: list[str] = []
        if "base_market" in sources:
            candidates.extend(base_market)
        if "top_turnover" in sources or "turnover" in sources:
            candidates.extend(turnover_ranked)
        if "top_volume" in sources:
            candidates.extend(volume_ranked)
        if "surge" in sources or "volume_spike" in sources:
            candidates.extend(surge_symbols)
        if "drop" in sources:
            candidates.extend(drop_symbols)
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
            snapshot = self.create_snapshot(
                event.symbol,
                snapshot_time=event.event_time,
                source_event_type=event.event_type,
                trigger_trace_ids=(event.trace_id,),
            )
            return {
                "accepted": True,
                "event_type": event.event_type.value,
                "reason": None,
                "snapshot": snapshot,
                "evaluation_snapshot": None,
            }

        batch = self.buffer_tick(event)
        if batch:
            apply_result = self._apply_events(batch)
            trace_ids = self._collect_trace_ids(batch)
            closed_timeframes = tuple(sorted(apply_result.closed_candles))
            updated_timeframes = tuple(sorted(apply_result.updated_timeframes))
            triggers: list[EvaluationTrigger] = [EvaluationTrigger.ON_TICK_BATCH]
            if updated_timeframes:
                triggers.append(EvaluationTrigger.ON_CANDLE_UPDATE)
            if closed_timeframes:
                triggers.append(EvaluationTrigger.ON_CANDLE_CLOSE)
            snapshot = self.create_snapshot(
                event.symbol,
                snapshot_time=batch[-1].event_time,
                source_event_type=EventType.TRADE_TICK,
                available_triggers=tuple(triggers),
                trigger_trace_ids=trace_ids,
                closed_timeframes=closed_timeframes,
                updated_timeframes=updated_timeframes,
            )
            evaluation_snapshot = None
            if closed_timeframes:
                evaluation_snapshot = self.create_snapshot(
                    event.symbol,
                    snapshot_time=self._closed_snapshot_time(apply_result.closed_candles),
                    candle_overrides=apply_result.closed_candles,
                    source_event_type=EventType.CANDLE_CLOSE,
                    available_triggers=(EvaluationTrigger.ON_CANDLE_CLOSE,),
                    trigger_trace_ids=trace_ids,
                    closed_timeframes=closed_timeframes,
                    updated_timeframes=updated_timeframes,
                    persist=False,
                )
            return {
                "accepted": True,
                "event_type": event.event_type.value,
                "reason": "tick_batch_flushed",
                "snapshot": snapshot,
                "evaluation_snapshot": evaluation_snapshot,
            }

        if event.event_type != EventType.TRADE_TICK:
            apply_result = self._apply_event(event)
            closed_timeframes = tuple(sorted(apply_result.closed_candles))
            updated_timeframes = tuple(sorted(apply_result.updated_timeframes))
            triggers: tuple[EvaluationTrigger, ...] = ()
            evaluation_snapshot = None
            if event.event_type == EventType.CANDLE_UPDATE:
                triggers = (EvaluationTrigger.ON_CANDLE_UPDATE,)
            if event.event_type == EventType.CANDLE_CLOSE:
                triggers = (EvaluationTrigger.ON_CANDLE_CLOSE,)
            snapshot = self.create_snapshot(
                event.symbol,
                snapshot_time=event.event_time,
                source_event_type=event.event_type,
                available_triggers=triggers,
                trigger_trace_ids=(event.trace_id,),
                closed_timeframes=closed_timeframes,
                updated_timeframes=updated_timeframes,
            )
            if event.event_type == EventType.CANDLE_CLOSE:
                evaluation_snapshot = snapshot
            return {
                "accepted": True,
                "event_type": event.event_type.value,
                "reason": None,
                "snapshot": snapshot,
                "evaluation_snapshot": evaluation_snapshot,
            }

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

    def _apply_events(self, events: list[NormalizedEvent]) -> _ApplyResult:
        merged = _ApplyResult(updated_timeframes=set(), closed_candles={})
        for event in events:
            result = self._apply_event(event)
            merged.updated_timeframes.update(result.updated_timeframes)
            merged.closed_candles.update(result.closed_candles)
        return merged

    def _apply_event(self, event: NormalizedEvent) -> _ApplyResult:
        result = _ApplyResult(updated_timeframes=set(), closed_candles={})
        symbol = event.symbol
        price = event.payload.get("trade_price") or event.payload.get("price")
        if isinstance(price, int | float):
            self._latest_price[symbol] = float(price)

        volume_24h = event.payload.get("acc_trade_volume_24h")
        if isinstance(volume_24h, int | float):
            self._volume_24h[symbol] = float(volume_24h)

        if event.event_type == EventType.TRADE_TICK and isinstance(price, int | float):
            self._record_trade_flow(event)
            trade_result = self._apply_trade_tick(event, float(price))
            result.updated_timeframes.update(trade_result.updated_timeframes)
            result.closed_candles.update(trade_result.closed_candles)

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
            result.updated_timeframes.add(timeframe)
            if event.event_type == EventType.CANDLE_CLOSE:
                closed_candle = self._copy_candle(candle, is_closed=True, last_update=event.event_time)
                self._append_closed_candle(symbol, timeframe, closed_candle)
                result.closed_candles[timeframe] = closed_candle

        return result

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

    def _apply_trade_tick(self, event: NormalizedEvent, trade_price: float) -> _ApplyResult:
        symbol = event.symbol
        trade_volume = self._as_float(event.payload.get("trade_volume") or event.payload.get("volume"), 0.0)
        result = _ApplyResult(updated_timeframes=set(), closed_candles={})
        symbol_candles = self._candles.setdefault(symbol, {})

        for timeframe in self.CANDLE_TIMEFRAMES:
            result.updated_timeframes.add(timeframe)
            candle_start = self._floor_time(event.event_time, timeframe)
            existing = symbol_candles.get(timeframe)
            if existing is None:
                symbol_candles[timeframe] = CandleState(
                    symbol=symbol,
                    timeframe=timeframe,
                    open=trade_price,
                    high=trade_price,
                    low=trade_price,
                    close=trade_price,
                    volume=trade_volume,
                    candle_start=candle_start,
                    is_closed=False,
                    last_update=event.event_time,
                )
                continue

            if existing.candle_start != candle_start:
                closed_candle = self._copy_candle(existing, is_closed=True)
                self._append_closed_candle(symbol, timeframe, closed_candle)
                result.closed_candles[timeframe] = closed_candle
                symbol_candles[timeframe] = CandleState(
                    symbol=symbol,
                    timeframe=timeframe,
                    open=trade_price,
                    high=trade_price,
                    low=trade_price,
                    close=trade_price,
                    volume=trade_volume,
                    candle_start=candle_start,
                    is_closed=False,
                    last_update=event.event_time,
                )
                continue

            existing.high = max(existing.high, trade_price)
            existing.low = min(existing.low, trade_price)
            existing.close = trade_price
            existing.volume += trade_volume
            existing.last_update = event.event_time

        return result

    def _record_trade_flow(self, event: NormalizedEvent) -> None:
        side_raw = event.payload.get("ask_bid") or event.payload.get("ab")
        side = str(side_raw).strip().upper()
        if side not in {"BID", "ASK"}:
            return

        volume = self._as_float(event.payload.get("trade_volume") or event.payload.get("volume"), 0.0)
        if volume <= 0:
            return

        history = self._trade_flow.setdefault(event.symbol, deque())
        history.append(_TradeFlowEntry(event_time=event.event_time, side=side, volume=volume))
        self._prune_trade_flow(event.symbol, event.event_time)

    def _entry_rate_snapshot(self, symbol: str, now: datetime) -> tuple[float | None, float | None]:
        history = self._trade_flow.get(symbol)
        if not history:
            return None, None

        self._prune_trade_flow(symbol, now)
        history = self._trade_flow.get(symbol)
        if not history:
            return None, None

        buy_volume = 0.0
        sell_volume = 0.0
        for item in history:
            if item.side == "BID":
                buy_volume += item.volume
            elif item.side == "ASK":
                sell_volume += item.volume

        total_volume = buy_volume + sell_volume
        if total_volume <= 0:
            return None, None

        return (buy_volume / total_volume) * 100.0, (sell_volume / total_volume) * 100.0

    def _prune_trade_flow(self, symbol: str, now: datetime) -> None:
        history = self._trade_flow.get(symbol)
        if not history:
            return

        cutoff = now - self.ENTRY_RATE_WINDOW
        while history and history[0].event_time < cutoff:
            history.popleft()

        if not history:
            self._trade_flow.pop(symbol, None)

    def _history_for_snapshot(
        self,
        symbol: str,
        candles: dict[str, CandleState],
    ) -> dict[str, tuple[CandleState, ...]]:
        history_by_timeframe = self._candle_history.get(symbol, {})
        snapshot_history: dict[str, tuple[CandleState, ...]] = {}
        for timeframe in set(history_by_timeframe).union(candles):
            history = list(history_by_timeframe.get(timeframe, deque()))
            current = candles.get(timeframe)
            if current is not None:
                if history and history[-1].candle_start == current.candle_start:
                    history[-1] = current
                elif not current.is_closed:
                    history.append(current)
            snapshot_history[timeframe] = tuple(history)
        return snapshot_history

    def _append_closed_candle(self, symbol: str, timeframe: str, candle: CandleState) -> None:
        history = self._candle_history.setdefault(symbol, {}).setdefault(timeframe, deque(maxlen=self.CANDLE_HISTORY_LIMIT))
        if history and history[-1].candle_start == candle.candle_start:
            history[-1] = candle
            return
        history.append(candle)

    def _copy_candle(
        self,
        candle: CandleState,
        *,
        is_closed: bool,
        last_update: datetime | None = None,
    ) -> CandleState:
        return CandleState(
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
            candle_start=candle.candle_start,
            is_closed=is_closed,
            last_update=last_update or candle.last_update,
        )

    def _closed_snapshot_time(self, closed_candles: dict[str, CandleState]) -> datetime:
        if not closed_candles:
            return datetime.now(UTC)
        close_times = [
            candle.candle_start + self._timeframe_delta(timeframe)
            for timeframe, candle in closed_candles.items()
        ]
        return max(close_times)

    def _collect_trace_ids(self, events: list[NormalizedEvent]) -> tuple[str, ...]:
        trace_ids: list[str] = []
        seen: set[str] = set()
        for event in events:
            trace_id = event.trace_id.strip()
            if not trace_id or trace_id in seen:
                continue
            trace_ids.append(trace_id)
            seen.add(trace_id)
        return tuple(trace_ids)

    def _floor_time(self, value: datetime, timeframe: str) -> datetime:
        if timeframe.endswith("m"):
            minutes = int(timeframe[:-1])
            floored_minute = floor(value.minute / minutes) * minutes
            return value.replace(minute=floored_minute, second=0, microsecond=0)
        if timeframe.endswith("h"):
            hours = int(timeframe[:-1])
            floored_hour = floor(value.hour / hours) * hours
            return value.replace(hour=floored_hour, minute=0, second=0, microsecond=0)
        return value.replace(second=0, microsecond=0)

    def _timeframe_delta(self, timeframe: str) -> timedelta:
        if timeframe.endswith("m"):
            return timedelta(minutes=int(timeframe[:-1]))
        if timeframe.endswith("h"):
            return timedelta(hours=int(timeframe[:-1]))
        return timedelta(seconds=1)

    def _latest_symbol_update_time(self, symbol: str) -> datetime | None:
        candidates: list[datetime] = []
        latest_event_time = self._latest_event_time.get(symbol)
        if latest_event_time is not None:
            candidates.append(latest_event_time)

        snapshot = self._snapshots.get(symbol)
        if snapshot is not None:
            candidates.append(snapshot.snapshot_time)

        for candle in self._candles.get(symbol, {}).values():
            if candle.last_update is not None:
                candidates.append(candle.last_update)

        if not candidates:
            return None
        return max(candidates)
