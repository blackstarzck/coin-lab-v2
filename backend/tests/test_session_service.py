from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.services.session_service import SessionService
from app.core.config import Settings
from app.core.error_codes import ErrorCode
from app.core.exceptions import CoinLabError
from app.domain.entities.session import Signal
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.schemas.session import SessionCreate
from tests.support import populate_test_store


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
    return populate_test_store(store)


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


def test_create_session_uses_strategy_static_symbols_by_default() -> None:
    store = _store()
    version = store.get_strategy_version("stv_001")
    assert version is not None
    version.config_json["universe"] = {
        "mode": "static",
        "symbols": ["KRW-BTC", "KRW-XRP"],
    }
    store.update_strategy_version(version)
    service = SessionService(store, _settings())

    session = service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={},
        )
    )

    assert session.symbol_scope_json["mode"] == "static"
    assert session.symbol_scope_json["symbols"] == ["KRW-BTC", "KRW-XRP"]
    assert session.symbol_scope_json["active_symbols"] == ["KRW-BTC", "KRW-XRP"]


def test_list_session_signals_enriches_legacy_explain_payload_from_session_config() -> None:
    store = _store()
    version = store.get_strategy_version("stv_001")
    assert version is not None
    version.config_json = {
        "id": "btc_breakout_v1",
        "market": {"timeframes": ["5m"]},
        "entry": {
            "logic": "all",
            "conditions": [
                {
                    "type": "indicator_compare",
                    "left": {"kind": "indicator", "name": "ema", "params": {"length": 20}},
                    "operator": ">",
                    "right": {"kind": "indicator", "name": "ema", "params": {"length": 50}},
                },
                {
                    "type": "price_breakout",
                    "source": {"kind": "price", "field": "close"},
                    "operator": ">",
                    "reference": {"kind": "derived", "name": "highest_high", "params": {"lookback": 20, "exclude_current": True}},
                },
            ],
        },
        "backtest": {"initial_capital": 1_000_000},
    }
    store.update_strategy_version(version)
    service = SessionService(store, _settings())
    session = service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={"mode": "dynamic", "sources": ["top_turnover"], "max_symbols": 2},
        )
    )

    service.store.create_signal(
        Signal(
            id="sig_legacy_001",
            session_id=session.id,
            strategy_version_id=session.strategy_version_id,
            symbol="KRW-BTC",
            timeframe="5m",
            action="ENTER",
            signal_price=103_300_000.0,
            confidence=1.0,
            reason_codes=["MVP_STUB_>", "MVP_STUB_>"],
            snapshot_time=datetime.now(UTC),
            blocked=False,
            explain_payload=None,
        )
    )

    signals = service.list_session_signals(session.id)

    assert len(signals) == 1
    assert signals[0].explain_payload is not None
    assert signals[0].explain_payload["legacy_payload"] is True
    assert "entry.conditions[0]: ema(20) > ema(50)" in signals[0].explain_payload["matched_conditions"]
    assert "entry.conditions[1]: price.close > highest_high(20, exclude_current=true)" in signals[0].explain_payload["matched_conditions"]
    assert {"label": "ema20", "value": "legacy signal - value not persisted"} in signals[0].explain_payload["facts"]
    assert {"label": "entry.conditions[0].left.params.length", "value": 20} in signals[0].explain_payload["parameters"]
