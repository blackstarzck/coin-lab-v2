from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.domain.entities.market import MarketSnapshot


def test_price_websocket_streams_snapshot_and_incremental_updates(client: TestClient, container) -> None:
    now = datetime.now(UTC)
    container.stream_service.record_snapshot(
        MarketSnapshot(
            symbol="KRW-BTC",
            latest_price=151_250_000,
            candles={},
            volume_24h=None,
            snapshot_time=now,
            buy_entry_rate_pct=61.5,
            sell_entry_rate_pct=38.5,
        )
    )

    with client.websocket_connect("/ws/prices?symbols=KRW-BTC,KRW-ETH") as websocket:
        snapshot_message = websocket.receive_json()

        assert snapshot_message["type"] == "price_snapshot"
        assert isinstance(snapshot_message["trace_id"], str)
        assert snapshot_message["trace_id"].startswith("trc_")
        assert snapshot_message["symbols"] == [
            {
                "symbol": "KRW-BTC",
                "price": 151_250_000,
                "timestamp": now.isoformat().replace("+00:00", "Z"),
                "buy_entry_rate_pct": 61.5,
                "sell_entry_rate_pct": 38.5,
                "entry_rate_window_sec": 60,
            },
            {
                "symbol": "KRW-ETH",
                "price": None,
                "timestamp": None,
                "buy_entry_rate_pct": None,
                "sell_entry_rate_pct": None,
                "entry_rate_window_sec": None,
            },
        ]

        next_time = now + timedelta(seconds=1)
        container.stream_service.record_snapshot(
            MarketSnapshot(
                symbol="KRW-ETH",
                latest_price=4_250_000,
                candles={},
                volume_24h=None,
                snapshot_time=next_time,
                buy_entry_rate_pct=40.0,
                sell_entry_rate_pct=60.0,
            )
        )

        update_message = websocket.receive_json()

        assert update_message["type"] == "price_update"
        assert update_message["symbol"] == "KRW-ETH"
        assert update_message["price"] == 4_250_000
        assert update_message["timestamp"] == next_time.isoformat().replace("+00:00", "Z")
        assert update_message["buy_entry_rate_pct"] == 40.0
        assert update_message["sell_entry_rate_pct"] == 60.0
        assert update_message["entry_rate_window_sec"] == 60
