from __future__ import annotations

import pytest

from app.application.services.session_service import SessionService
from app.core.config import Settings
from app.core.error_codes import ErrorCode
from app.core.exceptions import CoinLabError
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.schemas.session import SessionCreate


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "app_env": "test",
        "log_level": "INFO",
        "allowed_origins": ["http://localhost:5173"],
        "store_backend": "memory",
        "database_url": None,
        "upbit_rest_base_url": "https://api.upbit.com",
        "upbit_ws_public_url": "wss://api.upbit.com/websocket/v1",
        "upbit_ws_private_url": "wss://api.upbit.com/websocket/v1/private",
        "upbit_access_key": "access-key",
        "upbit_secret_key": "secret-key",
        "live_trading_enabled": True,
        "live_require_order_test": True,
        "live_order_notional_krw": 5000,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _store() -> InMemoryLabStore:
    store = InMemoryLabStore()
    store.seed_defaults()
    return store


def test_create_paper_session_populates_runtime_defaults() -> None:
    service = SessionService(_store(), _settings())

    session = service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={"mode": "dynamic", "sources": ["top_turnover"], "max_symbols": 2},
        )
    )

    assert session.mode.value == "PAPER"
    assert session.status.value == "RUNNING"
    assert session.symbol_scope_json["active_symbols"] == ["KRW-BTC", "KRW-ETH"]
    assert session.performance_json["realized_pnl"] == 0.0
    assert session.performance_json["initial_capital"] == 1000000
    assert session.health_json["connection_state"] == "CONNECTED"
    assert session.config_snapshot["id"] == "btc_breakout_v1"


def test_live_session_requires_trading_enabled() -> None:
    service = SessionService(_store(), _settings(live_trading_enabled=False))

    with pytest.raises(CoinLabError) as exc_info:
        service.create_session(
            SessionCreate(
                mode="LIVE",
                strategy_version_id="stv_001",
                symbol_scope={"symbols": ["KRW-BTC"]},
                confirm_live=True,
                acknowledge_risk=True,
                order_test_passed=True,
            )
        )

    assert exc_info.value.error_code == ErrorCode.LIVE_MODE_SWITCH_BLOCKED


def test_live_session_requires_api_keys() -> None:
    service = SessionService(_store(), _settings(upbit_access_key=None))

    with pytest.raises(CoinLabError) as exc_info:
        service.create_session(
            SessionCreate(
                mode="LIVE",
                strategy_version_id="stv_001",
                symbol_scope={"symbols": ["KRW-BTC"]},
                confirm_live=True,
                acknowledge_risk=True,
                order_test_passed=True,
            )
        )

    assert exc_info.value.error_code == ErrorCode.LIVE_API_KEY_MISSING


def test_live_session_requires_minimum_notional() -> None:
    service = SessionService(_store(), _settings(live_order_notional_krw=4999))

    with pytest.raises(CoinLabError) as exc_info:
        service.create_session(
            SessionCreate(
                mode="LIVE",
                strategy_version_id="stv_001",
                symbol_scope={"symbols": ["KRW-BTC"]},
                confirm_live=True,
                acknowledge_risk=True,
                order_test_passed=True,
            )
        )

    assert exc_info.value.error_code == ErrorCode.LIVE_MODE_SWITCH_BLOCKED


def test_live_session_requires_order_test_when_guard_enabled() -> None:
    service = SessionService(_store(), _settings(live_require_order_test=True))

    with pytest.raises(CoinLabError) as exc_info:
        service.create_session(
            SessionCreate(
                mode="LIVE",
                strategy_version_id="stv_001",
                symbol_scope={"symbols": ["KRW-BTC"]},
                confirm_live=True,
                acknowledge_risk=True,
                order_test_passed=False,
            )
        )

    assert exc_info.value.error_code == ErrorCode.LIVE_MODE_SWITCH_BLOCKED


def test_live_session_succeeds_when_all_guards_pass() -> None:
    service = SessionService(_store(), _settings())

    session = service.create_session(
        SessionCreate(
            mode="LIVE",
            strategy_version_id="stv_001",
            symbol_scope={"symbols": ["KRW-BTC"]},
            confirm_live=True,
            acknowledge_risk=True,
            order_test_passed=True,
        )
    )

    assert session.mode.value == "LIVE"
    assert session.status.value == "RUNNING"
    assert session.symbol_scope_json["active_symbols"] == ["KRW-BTC"]
