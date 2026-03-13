from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.services.session_service import SessionService
from app.application.services.strategy_service import StrategyService
from app.application.services.strategy_validator import StrategyValidator
from app.core.config import Settings
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.schemas.session import SessionCreate
from tests.support import TEST_STRATEGY_IDS, populate_test_store


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


def test_strategy_service_aggregates_recent_session_performance() -> None:
    store = populate_test_store(InMemoryLabStore())
    session_service = SessionService(store, _settings())

    recent_session = session_service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={"symbols": ["KRW-BTC"]},
        )
    )
    recent_session.performance_json = {
        **recent_session.performance_json,
        "initial_capital": 1_000_000,
        "realized_pnl": 50_000,
        "unrealized_pnl": 25_000,
        "trade_count": 4,
        "winning_trade_count": 3,
    }
    recent_session.updated_at = datetime.now(UTC)
    store.update_session(recent_session)

    stale_session = session_service.create_session(
        SessionCreate(
            mode="PAPER",
            strategy_version_id="stv_001",
            symbol_scope={"symbols": ["KRW-ETH"]},
        )
    )
    stale_session.performance_json = {
        **stale_session.performance_json,
        "initial_capital": 1_000_000,
        "realized_pnl": 250_000,
        "unrealized_pnl": 0,
        "trade_count": 10,
        "winning_trade_count": 10,
    }
    stale_session.updated_at = datetime.now(UTC) - timedelta(days=8)
    store.update_session(stale_session)

    service = StrategyService(store, StrategyValidator())

    strategy = service.get_strategy(TEST_STRATEGY_IDS["btc_breakout"])

    assert strategy.last_7d_return_pct == 7.5
    assert strategy.last_7d_win_rate == 75.0


def test_strategy_service_returns_none_without_recent_sessions() -> None:
    store = populate_test_store(InMemoryLabStore())
    service = StrategyService(store, StrategyValidator())

    strategy = service.get_strategy(TEST_STRATEGY_IDS["eth_momentum"])

    assert strategy.last_7d_return_pct is None
    assert strategy.last_7d_win_rate is None
