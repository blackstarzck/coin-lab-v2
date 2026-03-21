from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.services.session_service import SessionService
from app.application.services.strategy_service import StrategyService
from app.application.services.strategy_validator import StrategyValidator
from app.core.config import Settings
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore
from app.infrastructure.repositories.default_strategy_seeds import (
    DEFAULT_OB_FVG_STRATEGY_KEY,
    DEFAULT_OB_FVG_VERSION_ID,
    seed_default_strategies,
)
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


def test_in_memory_seed_defaults_register_ob_fvg_strategy_version() -> None:
    store = InMemoryLabStore()
    seed_default_strategies(store)

    strategies = store.list_strategies()
    seeded = next((item for item in strategies if item.strategy_key == DEFAULT_OB_FVG_STRATEGY_KEY), None)

    assert seeded is not None
    assert seeded.latest_version_id == DEFAULT_OB_FVG_VERSION_ID

    version = store.get_strategy_version(DEFAULT_OB_FVG_VERSION_ID)

    assert version is not None
    assert version.is_validated is True
    assert version.config_json["plugin_id"] == "ob_fvg_bull_reclaim_v1"


def test_seed_defaults_links_latest_version_after_both_rows_exist() -> None:
    class RecordingStore(InMemoryLabStore):
        def __init__(self) -> None:
            super().__init__()
            self.created_strategy_latest_version_ids: list[str | None] = []
            self.updated_strategy_latest_version_ids: list[str | None] = []

        def create_strategy(self, strategy):  # type: ignore[override]
            self.created_strategy_latest_version_ids.append(strategy.latest_version_id)
            return super().create_strategy(strategy)

        def update_strategy(self, strategy):  # type: ignore[override]
            self.updated_strategy_latest_version_ids.append(strategy.latest_version_id)
            return super().update_strategy(strategy)

    store = RecordingStore()

    seed_default_strategies(store)

    assert store.created_strategy_latest_version_ids == [None]
    assert store.updated_strategy_latest_version_ids == [DEFAULT_OB_FVG_VERSION_ID]
