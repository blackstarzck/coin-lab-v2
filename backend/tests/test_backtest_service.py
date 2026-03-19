from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.application.services.backtest_service import BacktestService
from app.core.exceptions import NotFoundError
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.main import app
from app.schemas.backtest import BacktestRunRequest
from tests.support import populate_test_store


def _store() -> InMemoryLabStore:
    store = InMemoryLabStore()
    return populate_test_store(store)


def test_backtest_run_requires_existing_strategy_version() -> None:
    service = BacktestService(_store())

    with pytest.raises(NotFoundError):
        service.create_run(
            BacktestRunRequest(
                strategy_version_id="stv_missing",
                symbols=["KRW-BTC"],
                timeframes=["5m"],
                date_from=datetime.fromisoformat("2025-12-01T00:00:00+00:00"),
                date_to=datetime.fromisoformat("2026-03-01T00:00:00+00:00"),
            )
        )


def test_backtest_run_api_returns_404_for_missing_strategy_version() -> None:
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post(
        "/api/v1/backtests/run",
        json={
            "strategy_version_id": "stv_missing",
            "symbols": ["KRW-BTC"],
            "timeframes": ["5m"],
            "date_from": "2025-12-01T00:00:00Z",
            "date_to": "2026-03-01T00:00:00Z",
        },
    )

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "REQ_NOT_FOUND"


def test_backtest_run_uses_strategy_backtest_initial_capital() -> None:
    service = BacktestService(_store())

    run = service.create_run(
        BacktestRunRequest(
            strategy_version_id="stv_001",
            symbols=["KRW-BTC"],
            timeframes=["5m"],
            date_from=datetime.fromisoformat("2025-12-01T00:00:00+00:00"),
            date_to=datetime.fromisoformat("2026-03-01T00:00:00+00:00"),
        )
    )

    assert run.initial_capital == 1000000


def test_backtest_run_falls_back_to_strategy_static_symbols() -> None:
    store = _store()
    version = store.get_strategy_version("stv_001")
    assert version is not None
    version.config_json["universe"] = {
        "mode": "static",
        "symbols": ["KRW-BTC", "KRW-XRP"],
    }
    store.update_strategy_version(version)
    service = BacktestService(store)

    run = service.create_run(
        BacktestRunRequest(
            strategy_version_id="stv_001",
            symbols=[],
            timeframes=["5m"],
            date_from=datetime.fromisoformat("2025-12-01T00:00:00+00:00"),
            date_to=datetime.fromisoformat("2026-03-01T00:00:00+00:00"),
        )
    )

    assert run.symbols == ["KRW-BTC", "KRW-XRP"]


def test_backtest_run_replays_snapshot_series_and_persists_trades() -> None:
    store = _store()
    version = store.get_strategy_version("stv_001")
    assert version is not None
    version.config_json = {
        "id": "btc_breakout_backtest_v1",
        "type": "plugin",
        "plugin_id": "breakout_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "5m",
            "lookback": 3,
            "breakout_pct": 0.0,
            "exit_breakdown_pct": 0.0,
        },
        "entry": {},
        "exit": {},
        "market": {"exchange": "UPBIT", "market_types": ["KRW"], "timeframes": ["5m"], "trade_basis": "candle"},
        "universe": {"mode": "static", "symbols": ["KRW-BTC"]},
        "position": {"size_mode": "fixed_qty", "size_value": 1.0, "max_open_positions_per_symbol": 1, "max_concurrent_positions": 1},
        "risk": {"daily_loss_limit_pct": 0.03, "max_strategy_drawdown_pct": 0.1, "kill_switch_enabled": True},
        "execution": {"entry_order_type": "market", "exit_order_type": "market", "fee_model": "per_fill", "slippage_model": "fixed_bps"},
        "backtest": {"initial_capital": 1_000_000, "fee_bps": 0, "slippage_bps": 0, "fill_assumption": "next_bar_open"},
    }
    store.update_strategy_version(version)
    service = BacktestService(store)

    def _bar(close: float, candle_start: str, history: list[dict[str, object]]) -> dict[str, object]:
        return {
            "symbol": "KRW-BTC",
            "timeframe": "5m",
            "snapshot_time": candle_start,
            "candle_start": candle_start,
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 100.0,
            "is_closed": True,
            "history": history,
        }

    series = [
        _bar(100.0, "2026-01-01T00:00:00+00:00", []),
        _bar(101.0, "2026-01-01T00:05:00+00:00", [{"candle_start": "2026-01-01T00:00:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100.0, "is_closed": True}]),
        _bar(102.0, "2026-01-01T00:10:00+00:00", [
            {"candle_start": "2026-01-01T00:00:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100.0, "is_closed": True},
            {"candle_start": "2026-01-01T00:05:00+00:00", "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 100.0, "is_closed": True},
        ]),
        _bar(105.0, "2026-01-01T00:15:00+00:00", [
            {"candle_start": "2026-01-01T00:00:00+00:00", "open": 99.5, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 100.0, "is_closed": True},
            {"candle_start": "2026-01-01T00:05:00+00:00", "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 100.0, "is_closed": True},
            {"candle_start": "2026-01-01T00:10:00+00:00", "open": 101.5, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 100.0, "is_closed": True},
        ]),
        _bar(100.0, "2026-01-01T00:20:00+00:00", [
            {"candle_start": "2026-01-01T00:05:00+00:00", "open": 100.5, "high": 102.0, "low": 100.0, "close": 101.0, "volume": 100.0, "is_closed": True},
            {"candle_start": "2026-01-01T00:10:00+00:00", "open": 101.5, "high": 103.0, "low": 101.0, "close": 102.0, "volume": 100.0, "is_closed": True},
            {"candle_start": "2026-01-01T00:15:00+00:00", "open": 104.5, "high": 106.0, "low": 104.0, "close": 105.0, "volume": 100.0, "is_closed": True},
        ]),
    ]

    run = service.create_run(
        BacktestRunRequest(
            strategy_version_id="stv_001",
            symbols=["KRW-BTC"],
            timeframes=["5m"],
            date_from=datetime.fromisoformat("2026-01-01T00:00:00+00:00"),
            date_to=datetime.fromisoformat("2026-01-01T00:20:00+00:00"),
            execution_overrides={"snapshot_series": series},
        )
    )

    trades = service.get_trades(run.id)

    assert run.status == "COMPLETED"
    assert len(trades) == 1
    assert trades[0].symbol == "KRW-BTC"
    assert trades[0].entry_price == pytest.approx(104.5)
    assert trades[0].exit_price == pytest.approx(100.0)
    assert run.metrics["trade_count"] == 1
    equity_curve = service.get_equity_curve(run.id)
    assert isinstance(equity_curve, list)
    assert len(equity_curve) == 2
