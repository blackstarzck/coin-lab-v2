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


def seed_default_strategies(store: LabStore) -> None:
    existing_keys = {item.strategy_key for item in store.list_strategies()}
    if DEFAULT_OB_FVG_STRATEGY_KEY in existing_keys:
        return

    strategy, version = build_default_ob_fvg_strategy()
    existing_strategy = store.get_strategy(strategy.id)
    if existing_strategy is None:
        # Break the circular FK between strategies.latest_version_id and
        # strategy_versions.strategy_id by linking the version after both rows exist.
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


def _config_hash(config_json: dict[str, object]) -> str:
    payload = json.dumps(config_json, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"
