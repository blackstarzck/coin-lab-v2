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
