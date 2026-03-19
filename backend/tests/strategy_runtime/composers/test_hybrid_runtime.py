from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.strategy_runtime import HybridStrategyRuntime
from app.domain.entities.market import CandleState, ConnectionState, MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction


def _snapshot_with_history(closes: list[float], *, timeframe: str = "5m") -> MarketSnapshot:
    now = datetime.now(UTC)
    candles: list[CandleState] = []
    for index, close in enumerate(closes):
        candle_time = now - timedelta(minutes=(len(closes) - 1 - index) * 5)
        candles.append(
            CandleState(
                symbol="KRW-BTC",
                timeframe=timeframe,
                open=close - 0.5,
                high=close + 1.0,
                low=close - 1.0,
                close=close,
                volume=100.0 + index,
                candle_start=candle_time,
                is_closed=True,
                last_update=candle_time,
            )
        )
    current = candles[-1]
    return MarketSnapshot(
        symbol="KRW-BTC",
        latest_price=current.close,
        candles={timeframe: current},
        volume_24h=1_000.0,
        snapshot_time=current.candle_start,
        candle_history={timeframe: tuple(candles[:-1])},
        is_stale=False,
        connection_state=ConnectionState.CONNECTED,
    )


def test_hybrid_runtime_maps_breakout_composer_to_strategy_decision() -> None:
    runtime = HybridStrategyRuntime()
    strategy_config = {
        "type": "hybrid",
        "market": {"timeframes": ["5m"]},
        "hybrid": {
            "composer_id": "breakout_v1",
            "composer_config": {
                "timeframe": "5m",
                "lookback": 3,
                "breakout_pct": 0.0,
                "exit_breakdown_pct": 0.02,
            },
        },
    }

    decision = runtime.evaluate(strategy_config, _snapshot_with_history([100.0, 101.0, 102.0, 105.0]))

    assert decision.action == PluginAction.ENTER
    assert "PLUGIN_BREAKOUT_ENTRY" in decision.reason_codes


def test_hybrid_runtime_explain_includes_strategy_runtime_context() -> None:
    runtime = HybridStrategyRuntime()
    strategy_config = {
        "type": "hybrid",
        "market": {"timeframes": ["5m"]},
        "hybrid": {
            "composer_id": "breakout_v1",
            "composer_config": {
                "timeframe": "5m",
                "lookback": 3,
                "breakout_pct": 0.0,
                "exit_breakdown_pct": 0.02,
            },
        },
    }

    payload = runtime.explain(
        strategy_config,
        _snapshot_with_history([100.0, 101.0, 102.0, 105.0]),
        fallback_decision="ENTER",
    )

    assert payload["decision"] == "ENTER"
    runtime_context = payload["strategy_runtime"]
    assert isinstance(runtime_context, dict)
    entry_setup = runtime_context["entry_setup"]
    assert isinstance(entry_setup, dict)
    assert entry_setup["setup_type"] == "breakout_continuation_long"
