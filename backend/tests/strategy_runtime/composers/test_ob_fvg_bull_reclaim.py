from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.strategy_runtime import HybridStrategyRuntime
from app.domain.entities.market import CandleState, ConnectionState, MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction


def _candle_series(
    candles: list[dict[str, float]],
    *,
    symbol: str,
    timeframe: str,
    end_time: datetime,
) -> list[CandleState]:
    delta = _timeframe_delta(timeframe)
    series: list[CandleState] = []
    for index, candle in enumerate(candles):
        candle_time = end_time - (len(candles) - 1 - index) * delta
        series.append(
            CandleState(
                symbol=symbol,
                timeframe=timeframe,
                open=float(candle["open"]),
                high=float(candle["high"]),
                low=float(candle["low"]),
                close=float(candle["close"]),
                volume=float(candle.get("volume", 100.0 + index)),
                candle_start=candle_time,
                is_closed=True,
                last_update=candle_time,
            )
        )
    return series


def _snapshot() -> MarketSnapshot:
    symbol = "KRW-BTC"
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    candles_15m = _candle_series(
        [
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5},
            {"open": 101.0, "high": 103.0, "low": 100.0, "close": 102.0},
            {"open": 101.0, "high": 102.0, "low": 99.0, "close": 100.0},
            {"open": 100.0, "high": 108.0, "low": 99.8, "close": 107.5},
            {"open": 103.5, "high": 109.0, "low": 103.0, "close": 108.0},
        ],
        symbol=symbol,
        timeframe="15m",
        end_time=now,
    )
    candles_1h = _candle_series(
        [
            {"open": 102.0, "high": 110.0, "low": 100.0, "close": 105.0},
            {"open": 108.0, "high": 120.0, "low": 106.0, "close": 118.0},
            {"open": 114.0, "high": 115.0, "low": 104.0, "close": 110.0},
            {"open": 120.0, "high": 130.0, "low": 112.0, "close": 128.0},
            {"open": 122.0, "high": 125.0, "low": 110.0, "close": 121.0},
            {"open": 126.0, "high": 136.0, "low": 118.0, "close": 134.0},
        ],
        symbol=symbol,
        timeframe="1h",
        end_time=now - timedelta(hours=1),
    )
    current_15m = candles_15m[-1]
    current_1h = candles_1h[-1]
    return MarketSnapshot(
        symbol=symbol,
        latest_price=current_15m.close,
        candles={"15m": current_15m, "1h": current_1h},
        volume_24h=1_000.0,
        snapshot_time=current_15m.candle_start,
        candle_history={"15m": tuple(candles_15m[:-1]), "1h": tuple(candles_1h[:-1])},
        is_stale=False,
        connection_state=ConnectionState.CONNECTED,
    )


def _timeframe_delta(timeframe: str) -> timedelta:
    normalized = timeframe.lower()
    if normalized.endswith("m"):
        return timedelta(minutes=int(normalized[:-1]))
    if normalized.endswith("h"):
        return timedelta(hours=int(normalized[:-1]))
    raise ValueError(f"unsupported timeframe {timeframe}")


def test_hybrid_runtime_maps_ob_fvg_bull_reclaim_to_strategy_decision() -> None:
    runtime = HybridStrategyRuntime()
    strategy_config = {
        "type": "hybrid",
        "market": {"timeframes": ["15m", "1h"]},
        "hybrid": {
            "composer_id": "ob_fvg_bull_reclaim_v1",
            "composer_config": {
                "timeframe": "15m",
                "trend_timeframe": "1h",
                "swing_width": 1,
                "atr_length": 2,
                "atr_mult": 1.1,
                "body_ratio_threshold": 0.45,
                "ob_lookback": 3,
                "poi_expiry_bars": 8,
                "sl_buffer_pct": 0.001,
                "rr_target": 1.8,
                "time_exit_bars": 20,
                "require_prev_close": False,
            },
        },
    }

    decision = runtime.evaluate(strategy_config, _snapshot())

    assert decision.action == PluginAction.ENTER
    assert "PLUGIN_OB_FVG_BULL_RECLAIM_ENTRY" in decision.reason_codes


def test_hybrid_runtime_explain_includes_ob_fvg_runtime_context() -> None:
    runtime = HybridStrategyRuntime()
    strategy_config = {
        "type": "hybrid",
        "market": {"timeframes": ["15m", "1h"]},
        "hybrid": {
            "composer_id": "ob_fvg_bull_reclaim_v1",
            "composer_config": {
                "timeframe": "15m",
                "trend_timeframe": "1h",
                "swing_width": 1,
                "atr_length": 2,
                "atr_mult": 1.1,
                "body_ratio_threshold": 0.45,
                "ob_lookback": 3,
                "poi_expiry_bars": 8,
                "sl_buffer_pct": 0.001,
                "rr_target": 1.8,
                "time_exit_bars": 20,
                "require_prev_close": False,
            },
        },
    }

    payload = runtime.explain(strategy_config, _snapshot(), fallback_decision="ENTER")

    assert payload["decision"] == "ENTER"
    runtime_context = payload["strategy_runtime"]
    assert isinstance(runtime_context, dict)
    entry_setup = runtime_context["entry_setup"]
    assert isinstance(entry_setup, dict)
    assert entry_setup["setup_type"] == "ob_fvg_bull_reclaim_long"
    assert entry_setup["risk"]["max_holding_bars"] == 20
