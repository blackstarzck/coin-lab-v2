from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.services.monitoring_service import MonitoringService
from app.application.services.session_service import SessionService
from app.core.config import Settings
from app.domain.entities.session import Order, OrderState, Position, PositionState, RiskEvent, SessionStatus, Signal
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.schemas.session import SessionCreate
from tests.support import populate_test_store


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
    populate_test_store(store)
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
    paper_session.performance_json.update(
        {
            "initial_capital": 1_000_000,
            "realized_pnl": 120_000,
            "unrealized_pnl": 30_000,
            "trade_count": 4,
            "winning_trade_count": 3,
        }
    )
    live_session.performance_json.update(
        {
            "initial_capital": 2_000_000,
            "realized_pnl": -40_000,
            "unrealized_pnl": 15_000,
            "trade_count": 2,
            "winning_trade_count": 1,
        }
    )
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
    store.create_position(
        Position(
            id="pos_test_001",
            session_id=paper_session.id,
            strategy_version_id="stv_001",
            symbol="KRW-BTC",
            position_state=PositionState.OPEN,
            side="LONG",
            entry_time=now - timedelta(hours=2),
            avg_entry_price=142_000_000,
            quantity=0.08,
            stop_loss_price=139_000_000,
            take_profit_price=147_500_000,
            unrealized_pnl=30_000,
            unrealized_pnl_pct=2.11,
        )
    )
    store.create_order(
        Order(
            id="ord_test_001",
            session_id=paper_session.id,
            strategy_version_id="stv_001",
            symbol="KRW-BTC",
            order_role="ENTRY",
            order_type="MARKET",
            order_state=OrderState.FILLED,
            requested_price=142_000_000,
            executed_price=142_000_000,
            requested_qty=0.1,
            executed_qty=0.1,
            retry_count=0,
            submitted_at=now - timedelta(hours=3),
            filled_at=now - timedelta(hours=3),
        )
    )
    store.create_order(
        Order(
            id="ord_test_002",
            session_id=paper_session.id,
            strategy_version_id="stv_001",
            symbol="KRW-BTC",
            order_role="TAKE_PROFIT",
            order_type="MARKET",
            order_state=OrderState.FILLED,
            requested_price=145_000_000,
            executed_price=145_000_000,
            requested_qty=0.05,
            executed_qty=0.05,
            retry_count=0,
            submitted_at=now - timedelta(hours=1),
            filled_at=now - timedelta(hours=1),
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
    assert cards["stg_001"]["last_7d_return_pct"] == 15.0
    assert cards["stg_001"]["last_signal_at"] == now
    assert cards["stg_002"]["is_validated"] is True
    assert cards["stg_002"]["active_session_count"] == 1
    assert cards["stg_002"]["last_7d_return_pct"] == -1.25

    universe_symbols = {item["symbol"]: item for item in summary["universe_summary"]["symbols"]}
    assert universe_symbols["KRW-BTC"]["has_recent_signal"] is True
    assert universe_symbols["KRW-ETH"]["risk_blocked"] is True
    assert universe_symbols["KRW-ETH"]["active_compare_session_count"] == 2

    assert summary["risk_overview"]["active_alert_count"] == 1
    assert summary["risk_overview"]["blocked_signal_count_1h"] == 1
    assert summary["recent_signals"][0].id in {"sig_test_001", "sig_test_002"}

    dashboard = summary["dashboard"]
    assert dashboard["hero"]["active_strategy_count"] == 2
    assert dashboard["hero"]["headline_strategy_name"] == "BTC 돌파"
    assert len(dashboard["strategy_strip"]) == 2
    assert len(dashboard["market_strip"]) == 3
    assert dashboard["performance_history"]["series"][0]["strategy_name"] == "BTC 돌파"
    assert dashboard["live_activity"][0]["kind"] in {"signal", "order", "risk"}
    assert dashboard["recent_trades"][0]["symbol"] == "KRW-BTC"
    assert dashboard["leaderboard"][0]["strategy_name"] == "BTC 돌파"
    assert dashboard["leaderboard"][0]["return_pct"] == 15.0
    assert dashboard["strategy_details"][0]["active_position_count"] == 1
    assert dashboard["strategy_details"][0]["monitoring_state"] == "running"
    assert dashboard["strategy_details"][0]["tracked_symbols"] == ["KRW-BTC", "KRW-ETH"]
    assert dashboard["strategy_details"][1]["monitoring_state"] == "degraded"
    assert dashboard["market_details"][0]["symbol"].startswith("KRW-")
