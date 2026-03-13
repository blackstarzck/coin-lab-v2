from __future__ import annotations

from datetime import UTC, datetime

from app.domain.entities.strategy import Strategy, StrategyType, StrategyVersion
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore

TEST_STRATEGY_IDS = {
    "btc_breakout": "stg_001",
    "eth_momentum": "stg_002",
}

TEST_VERSION_IDS = {
    "btc_breakout": "stv_001",
    "eth_momentum": "stv_002",
}


def populate_test_store(store: InMemoryLabStore) -> InMemoryLabStore:
    if store.list_strategies():
        return store

    now = datetime.now(UTC)
    strategies = [
        Strategy(
            id=TEST_STRATEGY_IDS["btc_breakout"],
            strategy_key="btc_breakout",
            name="BTC 돌파",
            strategy_type=StrategyType.DSL,
            description="EMA와 돌파 조합 전략",
            is_active=True,
            latest_version_id=TEST_VERSION_IDS["btc_breakout"],
            latest_version_no=1,
            labels=["돌파", "추세"],
            created_at=now,
            updated_at=now,
        ),
        Strategy(
            id=TEST_STRATEGY_IDS["eth_momentum"],
            strategy_key="eth_momentum",
            name="ETH 모멘텀",
            strategy_type=StrategyType.PLUGIN,
            description="모멘텀 지속 전략",
            is_active=True,
            latest_version_id=TEST_VERSION_IDS["eth_momentum"],
            latest_version_no=1,
            labels=["모멘텀"],
            created_at=now,
            updated_at=now,
        ),
    ]
    versions = [
        StrategyVersion(
            id=TEST_VERSION_IDS["btc_breakout"],
            strategy_id=TEST_STRATEGY_IDS["btc_breakout"],
            version_no=1,
            schema_version="1.0.0",
            config_json={
                "id": "btc_breakout_v1",
                "entry": {"ema_fast": 7, "ema_slow": 21},
                "backtest": {"initial_capital": 1_000_000},
            },
            config_hash="sha256:test001",
            labels=["돌파", "추세"],
            notes="테스트용 BTC 돌파 전략",
            is_validated=True,
            validation_summary={"valid": True, "errors": [], "warnings": []},
            created_by="test",
            created_at=now,
        ),
        StrategyVersion(
            id=TEST_VERSION_IDS["eth_momentum"],
            strategy_id=TEST_STRATEGY_IDS["eth_momentum"],
            version_no=1,
            schema_version="1.0.0",
            config_json={
                "id": "eth_momentum_v1",
                "entry": {"rsi_min": 55, "rsi_max": 72},
                "backtest": {"initial_capital": 1_000_000},
            },
            config_hash="sha256:test002",
            labels=["모멘텀"],
            notes="테스트용 ETH 모멘텀 전략",
            is_validated=True,
            validation_summary={"valid": True, "errors": [], "warnings": []},
            created_by="test",
            created_at=now,
        ),
    ]

    for strategy in strategies:
        store.create_strategy(strategy)
    for version in versions:
        store.create_strategy_version(version)

    store.update_universe(["KRW-BTC", "KRW-ETH", "KRW-SOL"])
    return store
