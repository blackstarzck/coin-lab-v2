from __future__ import annotations

import importlib
from copy import deepcopy
from typing import Protocol, cast


class _Validator(Protocol):
    def validate(self, config_json: dict[str, object], strict: bool) -> dict[str, object]: ...


class _ValidatorFactory(Protocol):
    def __call__(self) -> _Validator: ...


StrategyValidator = cast(
    _ValidatorFactory,
    getattr(importlib.import_module("app.application.services.strategy_validator"), "StrategyValidator"),
)


def _base_config() -> dict[str, object]:
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


def _codes(items: list[dict[str, str]]) -> set[str]:
    return {item["code"] for item in items if "code" in item}


def _section(config: dict[str, object], key: str) -> dict[str, object]:
    value = config.get(key)
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _issues(result: dict[str, object], key: str) -> list[dict[str, str]]:
    value = result.get(key)
    if isinstance(value, list):
        return cast(list[dict[str, str]], value)
    return []


def test_valid_full_dsl() -> None:
    result = StrategyValidator().validate(_base_config(), strict=False)
    assert result["valid"] is True
    assert result["errors"] == []


def test_missing_required_field_market() -> None:
    config = _base_config()
    _ = config.pop("market")
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_MISSING_REQUIRED_FIELD" in _codes(_issues(result, "errors"))


def test_unknown_top_level_key() -> None:
    config = _base_config()
    config["foo"] = "bar"
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_UNKNOWN_TOP_LEVEL_KEY" in _codes(_issues(result, "errors"))


def test_invalid_enum_market_exchange() -> None:
    config = _base_config()
    market = _section(config, "market")
    market["exchange"] = "BINANCE"
    config["market"] = market
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_ENUM" in _codes(_issues(result, "errors"))


def test_invalid_enum_position_size_mode() -> None:
    config = _base_config()
    position = _section(config, "position")
    position["size_mode"] = "yolo"
    config["position"] = position
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_ENUM" in _codes(_issues(result, "errors"))


def test_invalid_enum_execution_slippage_model() -> None:
    config = _base_config()
    execution = _section(config, "execution")
    execution["slippage_model"] = "random"
    config["execution"] = execution
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_ENUM" in _codes(_issues(result, "errors"))


def test_valid_market_trigger_enum() -> None:
    config = _base_config()
    market = _section(config, "market")
    market["trigger"] = "ON_TICK_BATCH"
    config["market"] = market

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_invalid_market_trigger_enum() -> None:
    config = _base_config()
    market = _section(config, "market")
    market["trigger"] = "ON_EVERYTHING"
    config["market"] = market

    result = StrategyValidator().validate(config, strict=False)

    assert "DSL_INVALID_ENUM" in _codes(_issues(result, "errors"))


def test_invalid_operator_in_leaf() -> None:
    config = _base_config()
    entry = _section(config, "entry")
    conditions = cast(list[dict[str, object]], entry.get("conditions", []))
    first_leaf = deepcopy(conditions[0])
    first_leaf["operator"] = "~="
    config["entry"] = {"logic": "all", "conditions": [first_leaf]}
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_UNKNOWN_OPERATOR" in _codes(_issues(result, "errors"))


def test_unknown_leaf_type() -> None:
    config = _base_config()
    config["entry"] = {
        "logic": "all",
        "conditions": [{"type": "magic_indicator", "operator": ">", "left": 1, "right": 2}],
    }
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_UNKNOWN_OPERATOR" in _codes(_issues(result, "errors"))


def test_invalid_timeframe_reference_compare_to() -> None:
    config = _base_config()
    config["entry"] = {
        "logic": "all",
        "conditions": [
            {
                "type": "indicator_compare",
                "left": {"kind": "indicator", "name": "ema", "compare_to": "1h"},
                "operator": ">",
                "right": {"kind": "constant", "value": 0.0},
            }
        ],
    }
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_TIMEFRAME_REFERENCE" in _codes(_issues(result, "errors"))


def test_partial_take_profit_sum_gt_one() -> None:
    config = _base_config()
    config["exit"] = {
        "stop_loss_pct": 0.015,
        "partial_take_profits": [
            {"close_ratio": 0.6, "target_pct": 0.02},
            {"close_ratio": 0.6, "target_pct": 0.04},
        ],
    }
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_PARTIAL_TP_SUM" in _codes(_issues(result, "errors"))


def test_condition_depth_exceeded() -> None:
    config = _base_config()
    node: dict[str, object] = {
        "type": "indicator_compare",
        "left": {"kind": "indicator", "name": "ema"},
        "operator": ">",
        "right": {"kind": "indicator", "name": "ema"},
    }
    for _ in range(11):
        node = {"logic": "all", "conditions": [node]}
    config["entry"] = node
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_CONDITION_DEPTH" in _codes(_issues(result, "errors"))


def test_empty_conditions_array() -> None:
    config = _base_config()
    config["entry"] = {"logic": "all", "conditions": []}
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_EMPTY_CONDITIONS" in _codes(_issues(result, "errors"))


def test_invalid_source_ref_kind() -> None:
    config = _base_config()
    config["entry"] = {
        "logic": "all",
        "conditions": [
            {
                "type": "indicator_compare",
                "left": {"kind": "magic", "name": "ema"},
                "operator": ">",
                "right": {"kind": "constant", "value": 1},
            }
        ],
    }
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_SOURCE_REF" in _codes(_issues(result, "errors"))


def test_rsi_range_min_gt_max() -> None:
    config = _base_config()
    config["entry"] = {
        "logic": "all",
        "conditions": [
            {
                "type": "rsi_range",
                "source": {"kind": "indicator", "name": "rsi"},
                "min": 70,
                "max": 30,
            }
        ],
    }
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_THRESHOLD_RANGE" in _codes(_issues(result, "errors"))


def test_negative_stop_loss_pct() -> None:
    config = _base_config()
    config["exit"] = {"stop_loss_pct": -0.01, "take_profit_pct": 0.02}
    result = StrategyValidator().validate(config, strict=False)
    assert "DSL_INVALID_THRESHOLD_RANGE" in _codes(_issues(result, "errors"))


def test_valid_plugin_type_with_empty_entry_exit_stubs() -> None:
    config = _base_config()
    config["type"] = "plugin"
    config["plugin_id"] = "breakout_v1"
    config["plugin_version"] = "1.0.0"
    config["plugin_config"] = {"lookback": 20}
    config["entry"] = {}
    config["exit"] = {}
    result = StrategyValidator().validate(config, strict=False)
    assert result["valid"] is True
    assert _issues(result, "errors") == []
    assert "DSL_PLUGIN_AND_DSL_CONFLICT" in _codes(_issues(result, "warnings"))


def test_plugin_type_requires_plugin_id() -> None:
    config = _base_config()
    config["type"] = "plugin"
    config["plugin_version"] = "1.0.0"
    config["plugin_config"] = {}
    config["entry"] = {}
    config["exit"] = {}
    result = StrategyValidator().validate(config, strict=False)
    assert result["valid"] is False
    assert "DSL_PLUGIN_CONTRACT_INVALID" in _codes(_issues(result, "errors"))


def test_plugin_type_rejects_unknown_plugin_id() -> None:
    config = _base_config()
    config["type"] = "plugin"
    config["plugin_id"] = "unknown_plugin"
    config["plugin_version"] = "1.0.0"
    config["plugin_config"] = {}
    config["entry"] = {}
    config["exit"] = {}
    result = StrategyValidator().validate(config, strict=False)
    assert result["valid"] is False
    assert "DSL_PLUGIN_LOAD_FAILED" in _codes(_issues(result, "errors"))


def test_valid_smc_confluence_plugin_type() -> None:
    config = _base_config()
    config["type"] = "plugin"
    config["plugin_id"] = "smc_confluence_v1"
    config["plugin_version"] = "1.0.0"
    config["plugin_config"] = {
        "timeframe": "5m",
        "trend_lookback": 12,
        "order_block_lookback": 8,
        "displacement_min_body_ratio": 0.55,
        "displacement_min_pct": 0.003,
        "fvg_gap_pct": 0.001,
        "zone_retest_tolerance_pct": 0.0015,
        "exit_zone_break_pct": 0.002,
        "min_confluence_score": 3,
        "require_order_block": False,
        "require_fvg": False,
        "require_confirmation": True,
    }
    config["entry"] = {}
    config["exit"] = {}

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_valid_ob_fvg_bull_reclaim_plugin_type() -> None:
    config = _base_config()
    config["type"] = "plugin"
    config["plugin_id"] = "ob_fvg_bull_reclaim_v1"
    config["plugin_version"] = "1.0.0"
    config["plugin_config"] = {
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
    }
    config["entry"] = {}
    config["exit"] = {"time_stop_bars": 20}

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_valid_zenith_hazel_plugin_type() -> None:
    config = _base_config()
    config["type"] = "plugin"
    config["plugin_id"] = "zenith_hazel_v1"
    config["plugin_version"] = "1.0.0"
    config["plugin_config"] = {
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
    }
    config["entry"] = {}
    config["exit"] = {"time_stop_bars": 24}

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_valid_hybrid_type_with_registered_composer() -> None:
    config = _base_config()
    config["type"] = "hybrid"
    config["entry"] = {}
    config["hybrid"] = {
        "composer_id": "breakout_v1",
        "composer_config": {
            "timeframe": "5m",
            "lookback": 3,
            "breakout_pct": 0.0,
            "exit_breakdown_pct": 0.01,
        },
    }
    config["execution_modules"] = {
        "entry_policy": {"policy_id": "signal_price"},
        "sizing_policy": {"policy_id": "default_v1"},
    }

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_valid_hybrid_type_with_ob_fvg_bull_reclaim_composer() -> None:
    config = _base_config()
    config["type"] = "hybrid"
    config["entry"] = {}
    config["hybrid"] = {
        "composer_id": "ob_fvg_bull_reclaim_v1",
        "composer_config": {
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
        },
    }

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_hybrid_type_requires_registered_composer() -> None:
    config = _base_config()
    config["type"] = "hybrid"
    config["entry"] = {}
    config["hybrid"] = {"composer_id": "missing_composer", "composer_config": {}}

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is False
    assert "DSL_PLUGIN_LOAD_FAILED" in _codes(_issues(result, "errors"))


def test_strict_mode_warning_without_watchlist() -> None:
    config = _base_config()
    universe = _section(config, "universe")
    universe["sources"] = ["top_turnover"]
    config["universe"] = universe
    result = StrategyValidator().validate(config, strict=True)
    assert "DSL_UNIVERSE_TOP_TURNOVER_ONLY" in _codes(_issues(result, "warnings"))


def test_static_universe_with_symbols_is_valid() -> None:
    config = _base_config()
    universe = _section(config, "universe")
    universe["mode"] = "static"
    universe["symbols"] = ["KRW-BTC", "KRW-ETH"]
    config["universe"] = universe

    result = StrategyValidator().validate(config, strict=True)

    assert result["valid"] is True
    assert _issues(result, "errors") == []


def test_static_universe_requires_symbols() -> None:
    config = _base_config()
    universe = _section(config, "universe")
    universe["mode"] = "static"
    universe["symbols"] = []
    config["universe"] = universe

    result = StrategyValidator().validate(config, strict=False)

    assert "DSL_VALIDATION_FAILED" in _codes(_issues(result, "errors"))


def test_reentry_allows_zero_cooldown_bars() -> None:
    config = _base_config()
    reentry = _section(config, "reentry")
    reentry["allow"] = True
    reentry["cooldown_bars"] = 0
    config["reentry"] = reentry

    result = StrategyValidator().validate(config, strict=False)

    assert result["valid"] is True
    assert _issues(result, "errors") == []
