from __future__ import annotations

import pytest

from app.application.services.universe_service import UniverseService
from tests.support import populate_test_store


@pytest.fixture()
def service(store):
    _ = populate_test_store(store)
    return UniverseService(store)


def test_catalog_returns_top_turnover_symbols(service: UniverseService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        service,
        "_fetch_market_rows",
        lambda quote: [
            {"market": f"{quote}-BTC", "korean_name": "비트코인", "english_name": "Bitcoin", "market_warning": "NONE"},
            {"market": f"{quote}-ETH", "korean_name": "이더리움", "english_name": "Ethereum", "market_warning": "NONE"},
            {"market": f"{quote}-XRP", "korean_name": "리플", "english_name": "XRP", "market_warning": "NONE"},
        ],
    )
    monkeypatch.setattr(
        service,
        "_fetch_ticker_rows",
        lambda symbols: {
            "KRW-BTC": {"acc_trade_price_24h": 900_000_000_000, "trade_price": 150_000_000},
            "KRW-ETH": {"acc_trade_price_24h": 500_000_000_000, "trade_price": 5_000_000},
            "KRW-XRP": {"acc_trade_price_24h": 300_000_000_000, "trade_price": 900},
        },
    )

    result = service.catalog(limit=2)

    assert [item["symbol"] for item in result] == ["KRW-BTC", "KRW-ETH"]
    assert result[0]["korean_name"] == "비트코인"
    assert result[0]["turnover_24h_krw"] == 900_000_000_000


def test_catalog_search_filters_by_symbol_and_name(service: UniverseService, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        service,
        "_fetch_market_rows",
        lambda quote: [
            {"market": f"{quote}-BTC", "korean_name": "비트코인", "english_name": "Bitcoin", "market_warning": "NONE"},
            {"market": f"{quote}-ETH", "korean_name": "이더리움", "english_name": "Ethereum", "market_warning": "NONE"},
            {"market": f"{quote}-XRP", "korean_name": "리플", "english_name": "Ripple", "market_warning": "NONE"},
        ],
    )
    monkeypatch.setattr(
        service,
        "_fetch_ticker_rows",
        lambda symbols: {
            "KRW-BTC": {"acc_trade_price_24h": 900_000_000_000},
            "KRW-ETH": {"acc_trade_price_24h": 500_000_000_000},
            "KRW-XRP": {"acc_trade_price_24h": 300_000_000_000},
        },
    )

    by_name = service.catalog(query="리플", limit=10)
    by_symbol = service.catalog(query="krw-b", limit=10)

    assert [item["symbol"] for item in by_name] == ["KRW-XRP"]
    assert [item["symbol"] for item in by_symbol] == ["KRW-BTC"]


def test_catalog_falls_back_to_current_universe(service: UniverseService, monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(quote: str) -> list[dict[str, object]]:
        _ = quote
        raise RuntimeError("upbit unavailable")

    monkeypatch.setattr(service, "_fetch_market_rows", raise_error)

    result = service.catalog(limit=3)

    assert [item["symbol"] for item in result][:3] == ["KRW-BTC", "KRW-ETH", "KRW-SOL"]
