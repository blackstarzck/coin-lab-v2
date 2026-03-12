from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.monitoring_service import MonitoringService
from app.application.services.session_service import SessionService
from app.core.config import Settings
from app.domain.entities.session import RiskEvent, SessionStatus, Signal
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.schemas.session import SessionCreate


def _settings() -> Settings:
    return Settings(
        app_env="test",
        log_level="INFO",
        allowed_origins=["http://localhost:5173"],
        store_backend="memory",
        database_url=None,
        upbit_rest_base_url="https://api.upbit.com",
        upbit_ws_public_url="wss://api.upbit.com/websocket/v1",
        upbit_ws_private_url="wss://api.upbit.com/websocket/v1/private",
        upbit_access_key="access-key",
        upbit_secret_key="secret-key",
        live_trading_enabled=True,
        live_require_order_test=True,
        live_order_notional_krw=5000,
    )


def test_monitoring_summary_reflects_validation_sessions_signals_and_risk() -> None:
    store = InMemoryLabStore()
    store.seed_defaults()
    session_service = SessionService(store, _settings())

    paper_session = session_service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={"mode": "dynamic", "max_symbols": 2},
        )
    )
    live_session = session_service.create_session(
        SessionCreate(
            mode="LIVE",
            strategy_version_id="stv_002",
            symbol_scope={"symbols": ["KRW-ETH"]},
            confirm_live=True,
            acknowledge_risk=True,
            order_test_passed=True,
        )
    )
    live_session.health_json["connection_state"] = "DEGRADED"
    live_session.status = SessionStatus.RUNNING

    now = datetime.now(UTC)
    store.create_signal(
        Signal(
            id="sig_test_001",
            session_id=paper_session.id,
            strategy_version_id="stv_001",
            symbol="KRW-BTC",
            timeframe="5m",
            action="ENTER",
            signal_price=143500000,
            confidence=0.78,
            reason_codes=["EMA_BULLISH"],
            snapshot_time=now,
            blocked=False,
        )
    )
    store.create_signal(
        Signal(
            id="sig_test_002",
            session_id=live_session.id,
            strategy_version_id="stv_002",
            symbol="KRW-ETH",
            timeframe="15m",
            action="EXIT",
            signal_price=4200000,
            confidence=0.64,
            reason_codes=["RISK_EXIT"],
            snapshot_time=now,
            blocked=True,
        )
    )
    store.create_risk_event(
        RiskEvent(
            id="rsk_test_001",
            session_id=live_session.id,
            strategy_version_id="stv_002",
            severity="WARN",
            code="DATA_SYMBOL_DEGRADED",
            symbol="KRW-ETH",
            message="ETH feed lag exceeds threshold",
            payload_preview={"late_event_count_5m": 6},
            created_at=now,
        )
    )

    summary = MonitoringService(store).get_summary()

    assert summary["status_bar"]["running_session_count"] == 2
    assert summary["status_bar"]["paper_session_count"] == 1
    assert summary["status_bar"]["live_session_count"] == 1
    assert summary["status_bar"]["degraded_session_count"] == 1
    assert summary["status_bar"]["active_symbol_count"] == 2

    cards = {card["strategy_id"]: card for card in summary["strategy_cards"]}
    assert cards["stg_001"]["is_validated"] is True
    assert cards["stg_001"]["active_session_count"] == 1
    assert cards["stg_001"]["last_signal_at"] == now
    assert cards["stg_002"]["is_validated"] is True
    assert cards["stg_002"]["active_session_count"] == 1

    universe_symbols = {item["symbol"]: item for item in summary["universe_summary"]["symbols"]}
    assert universe_symbols["KRW-BTC"]["has_recent_signal"] is True
    assert universe_symbols["KRW-ETH"]["risk_blocked"] is True
    assert universe_symbols["KRW-ETH"]["active_compare_session_count"] == 2

    assert summary["risk_overview"]["active_alert_count"] == 1
    assert summary["risk_overview"]["blocked_signal_count_1h"] == 1
    assert summary["recent_signals"][0].id in {"sig_test_001", "sig_test_002"}
