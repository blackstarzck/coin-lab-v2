from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime

from .entities.session import LogEntry
from .entities.strategy import Strategy, StrategyType, StrategyVersion


def base_strategy_config() -> dict[str, object]:
    return {
        "id": "btc_breakout_v1",
        "name": "BTC Breakout V1",
        "type": "dsl",
        "schema_version": "1.0.0",
        "description": "5m EMA breakout strategy",
        "enabled": True,
        "market": {
            "exchange": "UPBIT",
            "market_types": ["KRW"],
            "timeframes": ["5m", "15m"],
            "trade_basis": "candle",
        },
        "universe": {
            "mode": "dynamic",
            "sources": ["top_turnover", "watchlist"],
            "max_symbols": 10,
            "refresh_sec": 60,
            "filters": {
                "min_24h_turnover_krw": 1000000000,
                "exclude_symbols": [],
            },
        },
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
                    "reference": {
                        "kind": "derived",
                        "name": "highest_high",
                        "params": {"lookback": 20, "exclude_current": True},
                    },
                },
            ],
        },
        "reentry": {
            "allow": False,
            "cooldown_bars": 3,
            "require_reset": True,
            "reset_condition": {
                "type": "threshold_compare",
                "left": {"kind": "price", "field": "close"},
                "operator": "<",
                "right": {
                    "kind": "derived",
                    "name": "highest_high",
                    "params": {"lookback": 20},
                },
            },
        },
        "position": {
            "max_open_positions_per_symbol": 1,
            "allow_scale_in": False,
            "size_mode": "fixed_percent",
            "size_value": 0.1,
            "size_caps": {"min_pct": 0.02, "max_pct": 0.1},
            "max_concurrent_positions": 4,
        },
        "exit": {
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.03,
        },
        "risk": {
            "daily_loss_limit_pct": 0.03,
            "max_strategy_drawdown_pct": 0.1,
            "prevent_duplicate_entry": True,
            "max_order_retries": 2,
            "kill_switch_enabled": True,
        },
        "execution": {
            "entry_order_type": "limit",
            "exit_order_type": "limit",
            "limit_timeout_sec": 15,
            "fallback_to_market": True,
            "slippage_model": "fixed_bps",
            "fee_model": "per_fill",
        },
        "backtest": {
            "initial_capital": 1000000,
            "fee_bps": 5,
            "slippage_bps": 3,
            "latency_ms": 200,
            "fill_assumption": "next_bar_open",
        },
        "labels": ["trend", "breakout"],
        "notes": "",
    }


@dataclass(slots=True)
class SeedStrategyBundle:
    strategy: Strategy
    version: StrategyVersion


@dataclass(slots=True)
class SeedData:
    strategy_bundles: list[SeedStrategyBundle]
    universe_symbols: list[dict[str, object]]
    logs: list[LogEntry]


def default_seed_data(now: datetime | None = None) -> SeedData:
    seeded_at = now or datetime.now(UTC)

    btc_config = base_strategy_config()
    eth_config = deepcopy(btc_config)
    eth_config["id"] = "eth_momentum_v1"
    eth_config["name"] = "ETH Momentum V1"
    eth_config["description"] = "15m momentum continuation strategy"
    eth_config["labels"] = ["momentum"]
    eth_config["entry"] = {
        "logic": "all",
        "conditions": [
            {
                "type": "indicator_compare",
                "left": {"kind": "indicator", "name": "ema", "params": {"length": 10}},
                "operator": ">",
                "right": {"kind": "indicator", "name": "ema", "params": {"length": 30}},
            },
            {
                "type": "rsi_range",
                "source": {"kind": "indicator", "name": "rsi"},
                "min": 55,
                "max": 75,
            },
        ],
    }

    strategy_bundles = [
        SeedStrategyBundle(
            strategy=Strategy(
                id="stg_001",
                strategy_key="btc_breakout",
                name="BTC Breakout",
                strategy_type=StrategyType.DSL,
                description="EMA + breakout strategy",
                is_active=True,
                latest_version_id="stv_001",
                latest_version_no=1,
                labels=["trend", "breakout"],
                last_7d_return_pct=4.21,
                last_7d_win_rate=58.33,
                created_at=seeded_at,
                updated_at=seeded_at,
            ),
            version=StrategyVersion(
                id="stv_001",
                strategy_id="stg_001",
                version_no=1,
                schema_version="1.0.0",
                config_json=btc_config,
                config_hash="sha256:seed001",
                labels=["trend", "breakout"],
                notes="Seed version",
                is_validated=True,
                validation_summary={"valid": True, "errors": [], "warnings": []},
                created_by="system",
                created_at=seeded_at,
            ),
        ),
        SeedStrategyBundle(
            strategy=Strategy(
                id="stg_002",
                strategy_key="eth_momentum",
                name="ETH Momentum",
                strategy_type=StrategyType.DSL,
                description="Momentum continuation strategy",
                is_active=True,
                latest_version_id="stv_002",
                latest_version_no=1,
                labels=["momentum"],
                last_7d_return_pct=3.12,
                last_7d_win_rate=54.20,
                created_at=seeded_at,
                updated_at=seeded_at,
            ),
            version=StrategyVersion(
                id="stv_002",
                strategy_id="stg_002",
                version_no=1,
                schema_version="1.0.0",
                config_json=eth_config,
                config_hash="sha256:seed002",
                labels=["momentum"],
                notes="Seed version",
                is_validated=True,
                validation_summary={"valid": True, "errors": [], "warnings": []},
                created_by="system",
                created_at=seeded_at,
            ),
        ),
    ]

    universe_symbols = [
        {"symbol": "KRW-BTC", "turnover_24h_krw": 152300000000, "surge_score": 0.93, "selected": True},
        {"symbol": "KRW-ETH", "turnover_24h_krw": 87300000000, "surge_score": 0.89, "selected": True},
        {"symbol": "KRW-SOL", "turnover_24h_krw": 56300000000, "surge_score": 0.77, "selected": True},
    ]

    logs = [
        LogEntry(
            id="log_001",
            channel="strategy-execution",
            level="INFO",
            session_id=None,
            strategy_version_id="stv_001",
            symbol="KRW-BTC",
            event_type="SIGNAL_EMITTED",
            message="Entry signal emitted",
            payload={
                "snapshot_key": "KRW-BTC|5m|2026-03-10T03:05:00Z",
                "reason_codes": ["EMA_BULLISH", "HH20_BREAKOUT"],
            },
            logged_at=seeded_at,
        )
    ]

    return SeedData(
        strategy_bundles=strategy_bundles,
        universe_symbols=universe_symbols,
        logs=logs,
    )
