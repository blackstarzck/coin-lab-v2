"""Upbit websocket adapter for market event ingestion."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from uuid import uuid4

from ...core.trace import generate_trace_id
from ...domain.entities.market import EventType, NormalizedEvent

class UpbitWebsocketAdapter:
    """Builds subscriptions and normalizes raw Upbit websocket messages."""

    CHANNEL_MAP: dict[str, EventType] = {
        "trade": EventType.TRADE_TICK,
        "ticker": EventType.CANDLE_UPDATE,
        "raw_trade": EventType.TRADE_TICK,
        "raw_ticker": EventType.CANDLE_UPDATE,
    }

    def build_subscription_payload(
        self,
        symbols: list[str],
        channels: list[str],
    ) -> list[dict[str, object]]:
        unique_symbols = sorted({symbol for symbol in symbols if symbol})
        unique_channels = [channel for channel in dict.fromkeys(channels) if channel in {"trade", "ticker"}]
        ticket: dict[str, object] = {"ticket": generate_trace_id()}
        subscriptions: list[dict[str, object]] = [
            {"type": channel, "codes": unique_symbols} for channel in unique_channels
        ]
        format_hint: dict[str, object] = {"format": "DEFAULT"}
        return [ticket, *subscriptions, format_hint]

    def normalize_message(self, raw: dict[str, object], received_at: datetime) -> NormalizedEvent | None:
        raw_type = str(raw.get("type") or "").lower()
        event_type = self.CHANNEL_MAP.get(raw_type)
        if event_type is None:
            return None

        symbol = str(raw.get("code") or raw.get("symbol") or "").strip()
        if not symbol:
            return None

        event_time = self._extract_event_time(raw, fallback=received_at)
        sequence_no = self._safe_int(raw.get("sequential_id"))
        payload = self._normalize_payload(raw)

        if event_type == EventType.TRADE_TICK:
            trade_id = self._safe_int(raw.get("sequential_id"))
            dedupe_key = self._trade_dedupe_key(symbol, trade_id, payload)
        elif event_type == EventType.CANDLE_CLOSE:
            timeframe = str(payload.get("timeframe") or "1m")
            candle_start_ts = int(event_time.timestamp())
            dedupe_key = f"{symbol}:{timeframe}:{candle_start_ts}:close"
        else:
            dedupe_key = self._payload_hash_key(symbol, payload)

        trace_id = generate_trace_id()
        return NormalizedEvent(
            event_id=f"evt_{uuid4().hex}",
            dedupe_key=dedupe_key,
            symbol=symbol,
            timeframe=self._extract_timeframe(raw),
            event_type=event_type,
            event_time=event_time,
            sequence_no=sequence_no,
            received_at=received_at,
            source="upbit.ws",
            payload=payload,
            trace_id=trace_id,
        )

    def build_system_connection_event(
        self,
        connection_id: str,
        state: str,
        event_time: datetime,
    ) -> NormalizedEvent:
        ts_bucket = int(event_time.timestamp())
        dedupe_key = f"{connection_id}:{state}:{ts_bucket}"
        trace_id = generate_trace_id()
        return NormalizedEvent(
            event_id=f"evt_{uuid4().hex}",
            dedupe_key=dedupe_key,
            symbol="SYSTEM",
            timeframe=None,
            event_type=EventType.SYSTEM_CONNECTION,
            event_time=event_time,
            sequence_no=None,
            received_at=datetime.now(UTC),
            source="upbit.ws",
            payload={"connection_id": connection_id, "state": state},
            trace_id=trace_id,
        )

    def _normalize_payload(self, raw: dict[str, object]) -> dict[str, object]:
        payload = dict(raw)
        trade_price = self._safe_float(raw.get("trade_price") or raw.get("tp"))
        trade_volume = self._safe_float(raw.get("trade_volume") or raw.get("tv"))
        if trade_price is not None:
            payload["trade_price"] = trade_price
            payload["price"] = trade_price
            payload["close"] = trade_price
        if trade_volume is not None:
            payload["trade_volume"] = trade_volume
            payload["volume"] = trade_volume

        opening_price = self._safe_float(raw.get("opening_price") or raw.get("op"))
        high_price = self._safe_float(raw.get("high_price") or raw.get("hp"))
        low_price = self._safe_float(raw.get("low_price") or raw.get("lp"))
        if opening_price is not None:
            payload["open"] = opening_price
        if high_price is not None:
            payload["high"] = high_price
        if low_price is not None:
            payload["low"] = low_price

        acc_trade_price_24h = self._safe_float(raw.get("acc_trade_price_24h") or raw.get("atp24h"))
        acc_trade_volume_24h = self._safe_float(raw.get("acc_trade_volume_24h") or raw.get("atv24h"))
        if acc_trade_price_24h is not None:
            payload["acc_trade_price_24h"] = acc_trade_price_24h
        if acc_trade_volume_24h is not None:
            payload["acc_trade_volume_24h"] = acc_trade_volume_24h

        trade_timestamp = self._safe_int(raw.get("trade_timestamp") or raw.get("ttms"))
        if trade_timestamp is not None:
            payload["trade_timestamp"] = trade_timestamp

        sequential_id = self._safe_int(raw.get("sequential_id"))
        if sequential_id is not None:
            payload["sequential_id"] = sequential_id

        return payload

    def _extract_event_time(self, raw: dict[str, object], fallback: datetime) -> datetime:
        ts_value = self._safe_int(raw.get("trade_timestamp") or raw.get("timestamp") or raw.get("ttms") or raw.get("tms"))
        if ts_value is None:
            return fallback
        return datetime.fromtimestamp(ts_value / 1000, tz=UTC)

    def _extract_timeframe(self, raw: dict[str, object]) -> str | None:
        timeframe = raw.get("timeframe")
        if isinstance(timeframe, str) and timeframe:
            return timeframe
        return None

    def _trade_dedupe_key(self, symbol: str, trade_id: int | None, payload: dict[str, object]) -> str:
        if trade_id is not None:
            return f"{symbol}:{trade_id}"
        return self._payload_hash_key(symbol, payload)

    def _payload_hash_key(self, symbol: str, payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha256(encoded).hexdigest()[:16]
        return f"{symbol}:{digest}"

    def _safe_float(self, value: object) -> float | None:
        if value is None or not isinstance(value, int | float | str):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_int(self, value: object) -> int | None:
        if value is None or not isinstance(value, int | float | str):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
