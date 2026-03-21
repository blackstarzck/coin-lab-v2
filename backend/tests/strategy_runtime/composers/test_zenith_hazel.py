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
            {"open": 99.2, "high": 100.0, "low": 98.8, "close": 99.7, "volume": 96.0},
            {"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.8, "volume": 100.0},
            {"open": 100.8, "high": 102.0, "low": 100.4, "close": 101.6, "volume": 105.0},
            {"open": 101.6, "high": 103.0, "low": 101.0, "close": 102.4, "volume": 110.0},
            {"open": 102.4, "high": 104.0, "low": 101.9, "close": 103.5, "volume": 112.0},
            {"open": 103.5, "high": 105.0, "low": 103.0, "close": 104.4, "volume": 118.0},
            {"open": 104.4, "high": 106.0, "low": 103.8, "close": 105.5, "volume": 122.0},
            {"open": 105.6, "high": 109.5, "low": 105.2, "close": 108.8, "volume": 190.0},
        ],
        symbol=symbol,
        timeframe="15m",
        end_time=now,
    )
    candles_1h = _candle_series(
        [
            {"open": 96.0, "high": 100.0, "low": 94.0, "close": 99.0},
            {"open": 99.0, "high": 104.0, "low": 98.0, "close": 103.0},
            {"open": 103.0, "high": 108.0, "low": 101.0, "close": 107.0},
            {"open": 107.0, "high": 111.0, "low": 105.0, "close": 110.0},
            {"open": 110.0, "high": 114.0, "low": 108.0, "close": 113.0},
            {"open": 113.0, "high": 118.0, "low": 111.0, "close": 117.0},
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


def test_hybrid_runtime_maps_zenith_hazel_to_strategy_decision() -> None:
    runtime = HybridStrategyRuntime()
    strategy_config = {
        "type": "hybrid",
        "market": {"timeframes": ["15m", "1h"]},
        "hybrid": {
            "composer_id": "zenith_hazel_v1",
            "composer_config": {
                "timeframe": "15m",
                "regime_timeframe": "1h",
                "regime_lookback": 6,
                "swing_width": 1,
                "breakout_lookback": 4,
                "momentum_lookback": 3,
                "ema_fast_length": 3,
                "ema_slow_length": 5,
                "atr_length": 3,
                "min_regime_confidence": 0.1,
                "min_signal_confidence": 0.6,
                "min_signal_score": 4,
                "breakout_buffer_pct": 0.001,
                "min_momentum_pct": 0.003,
                "volume_surge_ratio": 1.15,
                "min_close_strength": 0.55,
                "high_volatility_atr_pct": 0.04,
                "stop_buffer_pct": 0.002,
                "exit_breakdown_pct": 0.005,
                "rr_target": 2.0,
                "time_exit_bars": 24,
                "allow_high_volatility_breakout": False,
            },
        },
    }

    decision = runtime.evaluate(strategy_config, _snapshot())

    assert decision.action == PluginAction.ENTER
    assert "PLUGIN_ZENITH_HAZEL_ENTRY" in decision.reason_codes


def test_hybrid_runtime_explain_includes_zenith_hazel_runtime_context() -> None:
    runtime = HybridStrategyRuntime()
    strategy_config = {
        "type": "hybrid",
        "market": {"timeframes": ["15m", "1h"]},
        "hybrid": {
            "composer_id": "zenith_hazel_v1",
            "composer_config": {
                "timeframe": "15m",
                "regime_timeframe": "1h",
                "regime_lookback": 6,
                "swing_width": 1,
                "breakout_lookback": 4,
                "momentum_lookback": 3,
                "ema_fast_length": 3,
                "ema_slow_length": 5,
                "atr_length": 3,
                "min_regime_confidence": 0.1,
                "min_signal_confidence": 0.6,
                "min_signal_score": 4,
                "breakout_buffer_pct": 0.001,
                "min_momentum_pct": 0.003,
                "volume_surge_ratio": 1.15,
                "min_close_strength": 0.55,
                "high_volatility_atr_pct": 0.04,
                "stop_buffer_pct": 0.002,
                "exit_breakdown_pct": 0.005,
                "rr_target": 2.0,
                "time_exit_bars": 24,
                "allow_high_volatility_breakout": False,
            },
        },
    }

    payload = runtime.explain(strategy_config, _snapshot(), fallback_decision="ENTER")

    assert payload["decision"] == "ENTER"
    runtime_context = payload["strategy_runtime"]
    assert isinstance(runtime_context, dict)
    entry_setup = runtime_context["entry_setup"]
    assert isinstance(entry_setup, dict)
    assert entry_setup["setup_type"] == "zenith_regime_momentum_long"
    assert entry_setup["risk"]["max_holding_bars"] == 24
    assert any(item["label"] == "composer.zenith_hazel_v1.regime_label" for item in payload["facts"])
