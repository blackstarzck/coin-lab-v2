from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json

from ...domain.entities.strategy import Strategy, StrategyType, StrategyVersion
from .lab_store import LabStore


DEFAULT_OB_FVG_STRATEGY_ID = "stg_seed_ob_fvg_001"
DEFAULT_OB_FVG_VERSION_ID = "stv_seed_ob_fvg_001"
DEFAULT_OB_FVG_STRATEGY_KEY = "xrp_ob_fvg_bull_reclaim"
DEFAULT_ZENITH_HAZEL_STRATEGY_ID = "stg_seed_zenith_hazel_001"
DEFAULT_ZENITH_HAZEL_VERSION_ID = "stv_seed_zenith_hazel_001"
DEFAULT_ZENITH_HAZEL_STRATEGY_KEY = "zenith_regime_momentum"


def seed_default_strategies(store: LabStore) -> None:
    for strategy, version in (build_default_ob_fvg_strategy(), build_default_zenith_hazel_strategy()):
        _seed_strategy_bundle(store, strategy, version)


def build_default_ob_fvg_strategy() -> tuple[Strategy, StrategyVersion]:
    now = datetime.now(UTC)
    config_json = _default_ob_fvg_config()
    validation_summary = {"valid": True, "errors": [], "warnings": []}
    version = StrategyVersion(
        id=DEFAULT_OB_FVG_VERSION_ID,
        strategy_id=DEFAULT_OB_FVG_STRATEGY_ID,
        version_no=1,
        schema_version="1.0.0",
        config_json=config_json,
        config_hash=_config_hash(config_json),
        labels=["smc", "orderblock", "fvg", "xrp"],
        notes="15m OB+FVG reclaim with 1h bull mode, seeded for live/paper experiments.",
        is_validated=True,
        validation_summary=validation_summary,
        created_by="system-seed",
        created_at=now,
    )
    strategy = Strategy(
        id=DEFAULT_OB_FVG_STRATEGY_ID,
        strategy_key=DEFAULT_OB_FVG_STRATEGY_KEY,
        name="XRP OB+FVG Bull Reclaim",
        strategy_type=StrategyType.PLUGIN,
        description="1h bull mode + 15m OB/FVG reclaim strategy for XRP experiments.",
        is_active=True,
        latest_version_id=version.id,
        latest_version_no=version.version_no,
        labels=["smc", "orderblock", "fvg", "xrp"],
        created_at=now,
        updated_at=now,
    )
    return strategy, version


def build_default_zenith_hazel_strategy() -> tuple[Strategy, StrategyVersion]:
    now = datetime.now(UTC)
    config_json = _default_zenith_hazel_config()
    validation_summary = {"valid": True, "errors": [], "warnings": []}
    version = StrategyVersion(
        id=DEFAULT_ZENITH_HAZEL_VERSION_ID,
        strategy_id=DEFAULT_ZENITH_HAZEL_STRATEGY_ID,
        version_no=1,
        schema_version="1.0.0",
        config_json=config_json,
        config_hash=_config_hash(config_json),
        labels=["zenith", "regime", "momentum", "trend"],
        notes="Zenith-inspired multi-regime momentum strategy adapted for Upbit large-cap KRW markets.",
        is_validated=True,
        validation_summary=validation_summary,
        created_by="system-seed",
        created_at=now,
    )
    strategy = Strategy(
        id=DEFAULT_ZENITH_HAZEL_STRATEGY_ID,
        strategy_key=DEFAULT_ZENITH_HAZEL_STRATEGY_KEY,
        name="Zenith Regime Momentum",
        strategy_type=StrategyType.PLUGIN,
        description="Zenith-inspired regime filter + momentum breakout strategy for Upbit majors.",
        is_active=True,
        latest_version_id=version.id,
        latest_version_no=version.version_no,
        labels=["zenith", "regime", "momentum", "trend"],
        created_at=now,
        updated_at=now,
    )
    return strategy, version


def _default_ob_fvg_config() -> dict[str, object]:
    return {
        "id": "xrp_ob_fvg_bull_reclaim_v1",
        "name": "XRP OB+FVG Bull Reclaim V1",
        "type": "plugin",
        "schema_version": "1.0.0",
        "description": "1h bull mode + 15m OB/FVG reclaim strategy",
        "enabled": True,
        "plugin_id": "ob_fvg_bull_reclaim_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "15m",
            "trend_timeframe": "1h",
            "swing_width": 3,
            "atr_length": 14,
            "atr_mult": 1.8,
            "body_ratio_threshold": 0.45,
            "ob_lookback": 8,
            "poi_expiry_bars": 24,
            "sl_buffer_pct": 0.001,
            "rr_target": 1.8,
            "time_exit_bars": 20,
            "require_prev_close": False,
            "bull_mode_off_exit_on_loss": True,
        },
        "market": {
            "exchange": "UPBIT",
            "market_types": ["KRW"],
            "timeframes": ["15m", "1h"],
            "trade_basis": "candle",
            "trigger": "ON_CANDLE_CLOSE",
        },
        "universe": {
            "mode": "static",
            "symbols": ["KRW-XRP"],
            "catalog_symbols": ["KRW-XRP"],
            "max_symbols": 1,
        },
        "entry": {},
        "reentry": {"enabled": False},
        "position": {
            "size_mode": "fixed_percent",
            "size_value": 0.1,
            "max_open_positions_per_symbol": 1,
            "max_concurrent_positions": 1,
        },
        "exit": {
            "time_stop_bars": 20,
            "runtime_condition_exit": {
                "fact_label": "composer.ob_fvg_bull_reclaim_v1.bull_mode_on",
                "when_value": False,
                "require_loss": True,
                "reason_code": "PLUGIN_OB_FVG_BULL_MODE_OFF",
            },
        },
        "risk": {
            "prevent_duplicate_entry": True,
            "daily_loss_limit_pct": 0.03,
            "max_strategy_drawdown_pct": 0.1,
            "kill_switch_enabled": True,
        },
        "execution": {
            "entry_order_type": "market",
            "exit_order_type": "market",
            "slippage_model": "fixed_bps",
            "fee_model": "per_fill",
        },
        "backtest": {
            "initial_capital": 1_000_000,
            "fee_bps": 10,
            "slippage_bps": 100,
            "fill_assumption": "next_bar_open",
        },
        "labels": ["smc", "orderblock", "fvg", "xrp"],
        "notes": "Seeded default strategy for OB+FVG live and paper experiments.",
    }


def _default_zenith_hazel_config() -> dict[str, object]:
    return {
        "id": "zenith_regime_momentum_v1",
        "name": "Zenith Regime Momentum V1",
        "type": "plugin",
        "schema_version": "1.0.0",
        "description": "Zenith-inspired multi-regime momentum breakout strategy adapted to Upbit majors.",
        "enabled": True,
        "plugin_id": "zenith_hazel_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "15m",
            "regime_timeframe": "1h",
            "regime_lookback": 12,
            "swing_width": 3,
            "breakout_lookback": 20,
            "momentum_lookback": 6,
            "ema_fast_length": 9,
            "ema_slow_length": 21,
            "atr_length": 14,
            "min_regime_confidence": 0.22,
            "min_signal_confidence": 0.72,
            "min_signal_score": 4,
            "breakout_buffer_pct": 0.001,
            "min_momentum_pct": 0.004,
            "volume_surge_ratio": 1.2,
            "min_close_strength": 0.58,
            "high_volatility_atr_pct": 0.03,
            "stop_buffer_pct": 0.002,
            "exit_breakdown_pct": 0.005,
            "rr_target": 2.0,
            "time_exit_bars": 24,
            "allow_high_volatility_breakout": False,
        },
        "market": {
            "exchange": "UPBIT",
            "market_types": ["KRW"],
            "timeframes": ["15m", "1h"],
            "trade_basis": "candle",
            "trigger": "ON_CANDLE_CLOSE",
        },
        "universe": {
            "mode": "static",
            "symbols": ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-LINK", "KRW-AVAX"],
            "catalog_symbols": ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-LINK", "KRW-AVAX"],
            "max_symbols": 6,
        },
        "entry": {},
        "reentry": {
            "allow": True,
            "cooldown_bars": 2,
            "require_reset": True,
            "reset_condition": {
                "type": "threshold_compare",
                "left": {"kind": "price", "field": "close"},
                "operator": "<",
                "right": {"kind": "indicator", "name": "ema", "params": {"length": 9}},
            },
        },
        "position": {
            "size_mode": "fixed_percent",
            "size_value": 0.08,
            "size_caps": {"min_pct": 0.03, "max_pct": 0.12},
            "max_open_positions_per_symbol": 1,
            "max_concurrent_positions": 3,
        },
        "exit": {
            "time_stop_bars": 24,
            "trailing_stop_pct": 0.018,
            "runtime_condition_exit": {
                "fact_label": "composer.zenith_hazel_v1.regime_entry_allowed",
                "when_value": False,
                "require_loss": True,
                "reason_code": "PLUGIN_ZENITH_HAZEL_REGIME_LOST",
            },
        },
        "risk": {
            "prevent_duplicate_entry": True,
            "daily_loss_limit_pct": 0.025,
            "max_strategy_drawdown_pct": 0.08,
            "max_order_retries": 1,
            "kill_switch_enabled": True,
        },
        "execution": {
            "entry_order_type": "market",
            "exit_order_type": "market",
            "limit_timeout_sec": 15,
            "fallback_to_market": True,
            "slippage_model": "fixed_bps",
            "fee_model": "per_fill",
        },
        "backtest": {
            "initial_capital": 1_000_000,
            "fee_bps": 10,
            "slippage_bps": 100,
            "latency_ms": 200,
            "fill_assumption": "next_bar_open",
        },
        "labels": ["zenith", "regime", "momentum", "trend"],
        "notes": "Approximation of Zenith Hazel paper-trading flow using Coin Lab plugin/runtime primitives on Upbit.",
    }


def _seed_strategy_bundle(store: LabStore, strategy: Strategy, version: StrategyVersion) -> None:
    existing_keys = {item.strategy_key for item in store.list_strategies()}
    if strategy.strategy_key in existing_keys and store.get_strategy_version(version.id) is not None:
        return

    existing_strategy = store.get_strategy(strategy.id)
    if existing_strategy is None:
        store.create_strategy(
            replace(
                strategy,
                latest_version_id=None,
                latest_version_no=None,
            )
        )
    if store.get_strategy_version(version.id) is None:
        store.create_strategy_version(version)
    if existing_strategy is None:
        store.update_strategy(strategy)


def _config_hash(config_json: dict[str, object]) -> str:
    payload = json.dumps(config_json, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
