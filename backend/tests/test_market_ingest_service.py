from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.services.market_ingest_service import MarketIngestService
from app.core import error_codes
from app.domain.entities.market import EventType, NormalizedEvent


def _event(
    dedupe_key: str,
    event_time: datetime,
    received_at: datetime,
    *,
    symbol: str = "KRW-BTC",
    event_type: EventType = EventType.TRADE_TICK,
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=f"evt-{dedupe_key}-{int(received_at.timestamp() * 1000)}",
        dedupe_key=dedupe_key,
        symbol=symbol,
        timeframe=None,
        event_type=event_type,
        event_time=event_time,
        sequence_no=None,
        received_at=received_at,
        source="test",
        payload={"trade_price": 100.0, "trade_volume": 1.0, "acc_trade_volume_24h": 12.0},
        trace_id="trc_test",
    )


def test_duplicate_event_dropped() -> None:
    service = MarketIngestService()
    now = datetime.now(UTC)
    event = _event("KRW-BTC:123", now, now)

    first = service.process_event(event)
    second = service.process_event(event)

    assert first["accepted"] is True
    assert second["accepted"] is False
    assert second["reason"] == error_codes.EVT_DUPLICATE_DROPPED


def test_out_of_order_event_dropped() -> None:
    service = MarketIngestService()
    now = datetime.now(UTC)
    latest = _event("KRW-BTC:1", now, now)
    old = _event("KRW-BTC:2", now - timedelta(seconds=3), now + timedelta(milliseconds=10))

    accepted_latest = service.process_event(latest)
    dropped_old = service.process_event(old)

    assert accepted_latest["accepted"] is True
    assert dropped_old["accepted"] is False
    assert dropped_old["reason"] == error_codes.EVT_OUT_OF_ORDER_DROPPED


def test_tick_buffer_flush_by_size() -> None:
    service = MarketIngestService()
    now = datetime.now(UTC)
    flushed = None

    for index in range(200):
        event_time = now + timedelta(milliseconds=index)
        received_at = now + timedelta(milliseconds=index)
        event = _event(f"KRW-BTC:{index}", event_time, received_at)
        flushed = service.buffer_tick(event)

    assert flushed is not None
    assert len(flushed) == 200
    assert flushed[0].event_time <= flushed[-1].event_time


def test_snapshot_freshness_stale() -> None:
    service = MarketIngestService()
    stale_tick_time = datetime.now(UTC) - timedelta(seconds=3)

    assert service.is_snapshot_stale(stale_tick_time, "tick") is True


# TC-EVT-003
def test_reconnect_gap_recovery_snapshot_freshness_tick_and_candle() -> None:
    """TC-EVT-003: Detect stale snapshots across tick and candle bases."""
    service = MarketIngestService()
    now = datetime.now(UTC)

    assert service.is_snapshot_stale(now - timedelta(milliseconds=500), "tick") is False
    assert service.is_snapshot_stale(now - timedelta(seconds=3), "tick") is True
    assert service.is_snapshot_stale(now - timedelta(seconds=30), "1m") is False
    assert service.is_snapshot_stale(now - timedelta(seconds=71), "1m") is True


# TC-EVT-004
def test_stale_snapshot_discard_candle_snapshot_stale() -> None:
    """TC-EVT-004: Candle snapshots older than threshold are stale."""
    service = MarketIngestService()

    assert service.is_snapshot_stale(datetime.now(UTC) - timedelta(seconds=71), "1m") is True


# TC-EVT-004
def test_stale_snapshot_discard_candle_snapshot_fresh() -> None:
    """TC-EVT-004: Candle snapshots within threshold are fresh."""
    service = MarketIngestService()

    assert service.is_snapshot_stale(datetime.now(UTC) - timedelta(seconds=30), "1m") is False


def test_reconnect_backoff_sequence() -> None:
    service = MarketIngestService()
    expected = {1: 1, 2: 2, 3: 5, 4: 10, 5: 20, 6: 30, 7: 30, 12: 30}

    for attempt, base in expected.items():
        delay = service.get_reconnect_delay(attempt)
        assert base * 0.8 <= delay <= base * 1.2


def test_candidate_pool_refresh() -> None:
    service = MarketIngestService()
    config: dict[str, object] = {
        "universe": {
            "max_symbols": 3,
            "sources": ["base_market", "turnover", "surge", "watchlist"],
        }
    }

    result = service.refresh_candidate_pool(config)

    assert len(result) == 3
    assert len(set(result)) == len(result)
    assert all(symbol.startswith("KRW-") for symbol in result)
