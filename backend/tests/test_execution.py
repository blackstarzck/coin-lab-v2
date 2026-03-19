from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

import pytest

from app.application.services.execution_service import ExecutionService
from app.application.services.fill_engine import FillEngine
from app.application.services.risk_guard_service import RiskGuardService
from app.application.services.signal_generator import SignalGenerator
from app.core import error_codes
from app.domain.entities.market import CandleState, ConnectionState, MarketSnapshot
from app.domain.entities.session import (
    ExecutionMode,
    ExitReason,
    FillResult,
    Position,
    PositionState,
    Session,
    SessionStatus,
    Signal,
    SignalAction,
)


def _base_strategy_config() -> dict[str, object]:
    return {
        "market": {"timeframes": ["1m"]},
        "entry": {"logic": "all", "conditions": [{"operator": "price_gt", "value": 1.0}]},
        "position": {
            "size_mode": "fixed_qty",
            "size_value": 1.0,
            "max_open_positions_per_symbol": 1,
            "max_concurrent_positions": 4,
        },
        "risk": {
            "prevent_duplicate_entry": True,
            "daily_loss_limit_pct": 0.03,
            "max_strategy_drawdown_pct": 0.1,
            "kill_switch_enabled": True,
        },
        "reentry": {"enabled": False},
        "execution": {
            "entry_order_type": "market",
            "limit_timeout_sec": 15,
            "fallback_to_market": True,
            "slippage_model": "fixed_bps",
            "fee_model": "per_fill",
        },
        "exit": {"stop_loss_pct": 0.05, "take_profit_pct": 0.05},
        "backtest": {
            "initial_capital": 1_000_000,
            "fee_bps": 10,
            "slippage_bps": 100,
            "fill_assumption": "next_bar_open",
        },
    }


def test_position_size_defaults_to_ten_percent_of_initial_capital() -> None:
    execution, _, _, _ = _services()
    qty = execution._calculate_position_size(  # noqa: SLF001 - sizing behavior is the unit under test
        {"backtest": {"initial_capital": 1_000_000}},
        _snapshot(latest=100.0, open_price=100.0, high=101.0, low=99.0, close=100.0),
    )

    assert qty == pytest.approx(1_000.0)


def test_fixed_amount_position_size_uses_krw_notional() -> None:
    execution, _, _, _ = _services()
    qty = execution._calculate_position_size(  # noqa: SLF001 - sizing behavior is the unit under test
        {
            "position": {"size_mode": "fixed_amount", "size_value": 250_000},
            "backtest": {"initial_capital": 1_000_000},
        },
        _snapshot(latest=100.0, open_price=100.0, high=101.0, low=99.0, close=100.0),
    )

    assert qty == pytest.approx(2_500.0)


def test_risk_per_trade_position_size_uses_runtime_stop_loss() -> None:
    execution, _, _, _ = _services()
    signal = Signal(
        id="sig_test_risk_001",
        session_id="ses_test_001",
        strategy_version_id="stv_test_001",
        symbol="KRW-BTC",
        timeframe="5m",
        action=SignalAction.ENTER.value,
        signal_price=100.0,
        confidence=1.0,
        reason_codes=["HYBRID_ENTRY"],
        snapshot_time=datetime.now(UTC),
        blocked=False,
        explain_payload={
            "strategy_runtime": {
                "entry_setup": {
                    "risk": {"stop_loss_price": 95.0, "take_profit_prices": [110.0]},
                    "invalidation_price": 95.0,
                }
            }
        },
    )
    qty = execution._calculate_position_size(  # noqa: SLF001 - sizing behavior is the unit under test
        {
            "position": {"size_mode": "risk_per_trade", "size_value": 0.01},
            "backtest": {"initial_capital": 1_000_000},
        },
        _snapshot(latest=100.0, open_price=100.0, high=101.0, low=99.0, close=100.0),
        signal,
    )

    assert qty == pytest.approx(2_000.0)


def _session() -> Session:
    now = datetime.now(UTC)
    return Session(
        id="ses_test_001",
        mode=ExecutionMode.BACKTEST,
        status=SessionStatus.RUNNING,
        strategy_version_id="stv_test_001",
        symbol_scope_json={"symbols": ["KRW-BTC"]},
        risk_overrides_json={},
        config_snapshot={},
        performance_json={"initial_capital": 1_000_000, "max_drawdown_pct": 0.0},
        health_json={},
        trace_id="trc_test",
        started_at=now,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )


def _snapshot(
    *,
    latest: float,
    open_price: float,
    high: float,
    low: float,
    close: float,
    snapshot_time: datetime | None = None,
) -> MarketSnapshot:
    now = snapshot_time or datetime.now(UTC)
    candle = CandleState(
        symbol="KRW-BTC",
        timeframe="1m",
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        candle_start=now,
        is_closed=True,
        last_update=now,
    )
    return MarketSnapshot(
        symbol="KRW-BTC",
        latest_price=latest,
        candles={"1m": candle},
        volume_24h=1000.0,
        snapshot_time=now,
        is_stale=False,
        connection_state=ConnectionState.CONNECTED,
    )


def _snapshot_with_history(
    closes: list[float],
    *,
    timeframe: str = "5m",
    snapshot_time: datetime | None = None,
) -> MarketSnapshot:
    now = snapshot_time or datetime.now(UTC)
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
    history = tuple(candles[:-1])
    return MarketSnapshot(
        symbol="KRW-BTC",
        latest_price=current.close,
        candles={timeframe: current},
        volume_24h=1000.0,
        snapshot_time=current.candle_start,
        candle_history={timeframe: history},
        is_stale=False,
        connection_state=ConnectionState.CONNECTED,
    )


def _snapshot_with_custom_candles(
    candles: list[dict[str, float]],
    *,
    timeframe: str = "5m",
    snapshot_time: datetime | None = None,
) -> MarketSnapshot:
    now = snapshot_time or datetime.now(UTC)
    series: list[CandleState] = []
    for index, candle in enumerate(candles):
        candle_time = now - timedelta(minutes=(len(candles) - 1 - index) * 5)
        series.append(
            CandleState(
                symbol="KRW-BTC",
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

    current = series[-1]
    history = tuple(series[:-1])
    return MarketSnapshot(
        symbol="KRW-BTC",
        latest_price=current.close,
        candles={timeframe: current},
        volume_24h=1000.0,
        snapshot_time=current.candle_start,
        candle_history={timeframe: history},
        is_stale=False,
        connection_state=ConnectionState.CONNECTED,
    )


def _position(*, stop: float, tp: float, qty: float = 1.0) -> Position:
    return Position(
        id="pos_test_001",
        session_id="ses_test_001",
        strategy_version_id="stv_test_001",
        symbol="KRW-BTC",
        position_state=PositionState.OPEN,
        side="LONG",
        entry_time=datetime.now(UTC),
        avg_entry_price=100.0,
        quantity=qty,
        stop_loss_price=stop,
        take_profit_price=tp,
        unrealized_pnl=0.0,
        unrealized_pnl_pct=0.0,
    )


def _services() -> tuple[ExecutionService, RiskGuardService, FillEngine, SignalGenerator]:
    risk_guard = RiskGuardService()
    fill_engine = FillEngine()
    signal_generator = SignalGenerator()
    return ExecutionService(risk_guard, fill_engine, signal_generator), risk_guard, fill_engine, signal_generator


def test_market_entry_fill() -> None:
    execution, _, _, _ = _services()
    result = execution.process_snapshot(
        _session(),
        _base_strategy_config(),
        _snapshot(latest=110.0, open_price=100.0, high=112.0, low=99.0, close=111.0),
    )

    assert result["accepted"] is True
    fill = cast(FillResult, result["fill"])
    position = cast(Position, result["position"])
    assert fill.filled is True
    assert fill.fill_price == pytest.approx(101.0)
    assert fill.fee_amount == pytest.approx(0.101)
    assert position.position_state == PositionState.OPEN


def test_limit_entry_no_fill() -> None:
    execution, _, _, _ = _services()
    config = _base_strategy_config()
    config["execution"] = {
        "entry_order_type": "limit",
        "limit_timeout_sec": 15,
        "fallback_to_market": False,
        "slippage_model": "fixed_bps",
    }
    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot(latest=100.0, open_price=103.0, high=105.0, low=101.0, close=104.0),
    )

    assert result["accepted"] is False
    fill = cast(FillResult, result["fill"])
    assert fill.filled is False


def test_limit_timeout_fallback_to_market() -> None:
    execution, _, _, _ = _services()
    config = _base_strategy_config()
    config["execution"] = {
        "entry_order_type": "limit",
        "limit_timeout_sec": 15,
        "fallback_to_market": True,
        "slippage_model": "fixed_bps",
    }
    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot(latest=100.0, open_price=103.0, high=105.0, low=101.0, close=104.0),
    )

    assert result["accepted"] is True
    assert cast(FillResult, result["fill"]).filled is True


def test_plugin_strategy_generates_entry_signal() -> None:
    execution, _, _, _ = _services()
    config = _base_strategy_config()
    config.update({
        "type": "plugin",
        "plugin_id": "breakout_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "5m",
            "lookback": 3,
            "breakout_pct": 0.0,
            "exit_breakdown_pct": 0.02,
        },
        "entry": {},
    })

    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot_with_history([100.0, 101.0, 102.0, 105.0]),
    )

    assert result["accepted"] is True
    signal = cast(Signal, result["signal"])
    assert signal.action == SignalAction.ENTER.value
    assert "PLUGIN_BREAKOUT_ENTRY" in signal.reason_codes


def test_plugin_strategy_exit_signal_closes_position() -> None:
    execution, risk_guard, _, _ = _services()
    position = _position(stop=50.0, tp=150.0)
    execution.sync_positions([position])
    risk_guard.register_position("ses_test_001", "KRW-BTC", PositionState.OPEN)

    config = _base_strategy_config()
    config.update({
        "type": "plugin",
        "plugin_id": "breakout_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "5m",
            "lookback": 3,
            "breakout_pct": 0.03,
            "exit_breakdown_pct": 0.0,
        },
        "entry": {},
    })

    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot_with_history([110.0, 109.0, 108.0, 105.0]),
    )

    assert result["accepted"] is True
    exits = cast(list[dict[str, object]], result["exits"])
    assert len(exits) == 1
    exit_signal = cast(Signal, exits[0]["signal"])
    assert exit_signal.action == SignalAction.EXIT.value
    assert "PLUGIN_BREAKDOWN_EXIT" in exit_signal.reason_codes


def test_smc_confluence_plugin_generates_entry_signal() -> None:
    execution, _, _, _ = _services()
    config = _base_strategy_config()
    config.update({
        "type": "plugin",
        "plugin_id": "smc_confluence_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "5m",
            "trend_lookback": 8,
            "order_block_lookback": 6,
            "displacement_min_body_ratio": 0.5,
            "displacement_min_pct": 0.01,
            "fvg_gap_pct": 0.005,
            "zone_retest_tolerance_pct": 0.002,
            "exit_zone_break_pct": 0.002,
            "min_confluence_score": 4,
            "require_order_block": True,
            "require_fvg": True,
            "require_confirmation": True,
        },
        "entry": {},
    })

    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot_with_custom_candles([
            {"open": 100.0, "high": 102.5, "low": 99.5, "close": 102.0},
            {"open": 102.0, "high": 104.5, "low": 101.5, "close": 104.0},
            {"open": 104.0, "high": 106.5, "low": 103.5, "close": 106.0},
            {"open": 106.0, "high": 108.0, "low": 105.5, "close": 107.0},
            {"open": 108.0, "high": 108.4, "low": 106.2, "close": 106.8},
            {"open": 106.9, "high": 112.0, "low": 106.6, "close": 111.2},
            {"open": 111.0, "high": 113.0, "low": 109.4, "close": 112.6},
            {"open": 112.4, "high": 113.2, "low": 111.8, "close": 112.9},
            {"open": 107.4, "high": 111.4, "low": 106.9, "close": 110.9},
        ]),
    )

    assert result["accepted"] is True
    signal = cast(Signal, result["signal"])
    assert signal.action == SignalAction.ENTER.value
    assert "PLUGIN_SMC_CONFLUENCE_ENTRY" in signal.reason_codes
    assert signal.explain_payload is not None
    runtime = cast(dict[str, object], signal.explain_payload["strategy_runtime"])
    assert cast(dict[str, object], runtime["entry_setup"])["setup_type"] == "smc_confluence_long"


def test_smc_confluence_plugin_exit_signal_closes_position() -> None:
    execution, risk_guard, _, _ = _services()
    position = _position(stop=50.0, tp=150.0)
    execution.sync_positions([position])
    risk_guard.register_position("ses_test_001", "KRW-BTC", PositionState.OPEN)

    config = _base_strategy_config()
    config.update({
        "type": "plugin",
        "plugin_id": "smc_confluence_v1",
        "plugin_version": "1.0.0",
        "plugin_config": {
            "timeframe": "5m",
            "trend_lookback": 8,
            "order_block_lookback": 6,
            "displacement_min_body_ratio": 0.5,
            "displacement_min_pct": 0.01,
            "fvg_gap_pct": 0.005,
            "zone_retest_tolerance_pct": 0.002,
            "exit_zone_break_pct": 0.002,
            "min_confluence_score": 4,
            "require_order_block": True,
            "require_fvg": True,
            "require_confirmation": True,
        },
        "entry": {},
    })

    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot_with_custom_candles([
            {"open": 100.0, "high": 102.5, "low": 99.5, "close": 102.0},
            {"open": 102.0, "high": 104.5, "low": 101.5, "close": 104.0},
            {"open": 104.0, "high": 106.5, "low": 103.5, "close": 106.0},
            {"open": 106.0, "high": 108.0, "low": 105.5, "close": 107.0},
            {"open": 108.0, "high": 108.4, "low": 106.2, "close": 106.8},
            {"open": 106.9, "high": 112.0, "low": 106.6, "close": 111.2},
            {"open": 111.0, "high": 113.0, "low": 109.4, "close": 112.6},
            {"open": 112.4, "high": 113.2, "low": 111.8, "close": 112.9},
            {"open": 108.8, "high": 109.0, "low": 104.5, "close": 104.6},
        ]),
    )

    assert result["accepted"] is True
    exits = cast(list[dict[str, object]], result["exits"])
    assert len(exits) == 1
    exit_signal = cast(Signal, exits[0]["signal"])
    assert exit_signal.action == SignalAction.EXIT.value
    assert "PLUGIN_SMC_EXIT_ORDER_BLOCK_BROKEN" in exit_signal.reason_codes


def test_hybrid_strategy_generates_entry_signal() -> None:
    execution, _, _, _ = _services()
    config = _base_strategy_config()
    config.update({
        "type": "hybrid",
        "entry": {},
        "hybrid": {
            "composer_id": "breakout_v1",
            "composer_config": {
                "timeframe": "5m",
                "lookback": 3,
                "breakout_pct": 0.0,
                "exit_breakdown_pct": 0.02,
            },
        },
        "execution_modules": {
            "entry_policy": {"policy_id": "signal_price"},
            "sizing_policy": {"policy_id": "default_v1"},
        },
    })

    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot_with_history([100.0, 101.0, 102.0, 105.0]),
    )

    assert result["accepted"] is True
    signal = cast(Signal, result["signal"])
    assert signal.action == SignalAction.ENTER.value
    assert "PLUGIN_BREAKOUT_ENTRY" in signal.reason_codes
    assert signal.explain_payload is not None
    assert signal.explain_payload["decision"] == "ENTER"
    runtime = cast(dict[str, object], signal.explain_payload["strategy_runtime"])
    assert cast(dict[str, object], runtime["entry_setup"])["setup_type"] == "breakout_continuation_long"


def test_hybrid_strategy_exit_signal_closes_position() -> None:
    execution, risk_guard, _, _ = _services()
    position = _position(stop=50.0, tp=150.0)
    execution.sync_positions([position])
    risk_guard.register_position("ses_test_001", "KRW-BTC", PositionState.OPEN)

    config = _base_strategy_config()
    config.update({
        "type": "hybrid",
        "entry": {},
        "hybrid": {
            "composer_id": "breakout_v1",
            "composer_config": {
                "timeframe": "5m",
                "lookback": 3,
                "breakout_pct": 0.03,
                "exit_breakdown_pct": 0.0,
            },
        },
    })

    result = execution.process_snapshot(
        _session(),
        config,
        _snapshot_with_history([110.0, 109.0, 108.0, 105.0]),
    )

    assert result["accepted"] is True
    exits = cast(list[dict[str, object]], result["exits"])
    assert len(exits) == 1
    exit_signal = cast(Signal, exits[0]["signal"])
    assert exit_signal.action == SignalAction.EXIT.value
    assert "PLUGIN_BREAKDOWN_EXIT" in exit_signal.reason_codes


def test_stop_loss_triggered() -> None:
    fill_engine = FillEngine()
    reason = fill_engine.evaluate_exit_triggers(
        position=_position(stop=95.0, tp=130.0),
        current_price=94.0,
        candle_high=99.0,
        candle_low=94.0,
        exit_config={"stop_loss_pct": 0.05, "take_profit_pct": 0.3},
        bar_count=1,
    )
    assert reason == ExitReason.STOP_LOSS


def test_take_profit_triggered() -> None:
    fill_engine = FillEngine()
    reason = fill_engine.evaluate_exit_triggers(
        position=_position(stop=90.0, tp=103.0),
        current_price=104.0,
        candle_high=104.0,
        candle_low=101.0,
        exit_config={"stop_loss_pct": 0.1, "take_profit_pct": 0.03},
        bar_count=1,
    )
    assert reason == ExitReason.TAKE_PROFIT


def test_intra_bar_conflict_conservative() -> None:
    fill_engine = FillEngine()
    reason = fill_engine.evaluate_exit_triggers(
        position=_position(stop=95.0, tp=103.0),
        current_price=100.0,
        candle_high=104.0,
        candle_low=94.0,
        exit_config={"stop_loss_pct": 0.05, "take_profit_pct": 0.03},
        bar_count=1,
    )
    assert reason == ExitReason.STOP_LOSS_INTRA_BAR_CONSERVATIVE


# TC-BT-005
def test_partial_take_profit_chain_applies_first_two_levels_only() -> None:
    """TC-BT-005: Partial take-profit chain."""
    fill_engine = FillEngine()
    position = _position(stop=90.0, tp=130.0, qty=10.0)
    partial_take_profits: list[dict[str, object]] = [
        {"at_profit_pct": 0.02, "close_ratio": 0.3},
        {"at_profit_pct": 0.05, "close_ratio": 0.3},
        {"at_profit_pct": 0.10, "close_ratio": 0.4},
    ]

    fills = fill_engine.process_partial_take_profits(position, 106.0, partial_take_profits)

    assert len(fills) == 2
    assert fills[0].fill_qty == pytest.approx(3.0)
    assert fills[1].fill_qty == pytest.approx(3.0)
    assert all(fill.filled is True for fill in fills)
    assert all(fill.exit_reason == ExitReason.TAKE_PROFIT.value for fill in fills)
    remaining_qty = position.quantity - sum(fill.fill_qty for fill in fills)
    assert remaining_qty == pytest.approx(4.0)


def test_duplicate_signal_rejected() -> None:
    _, _, _, signal_generator = _services()
    config = _base_strategy_config()
    snap = _snapshot(latest=110.0, open_price=100.0, high=111.0, low=99.0, close=110.0)

    first = signal_generator.evaluate(config, snap, "ses_test_001", "stv_test_001")
    second = signal_generator.evaluate(config, snap, "ses_test_001", "stv_test_001")

    assert first is not None
    assert second is not None
    assert second.blocked is True
    assert error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED in second.reason_codes
    assert second.explain_payload is not None
    assert second.explain_payload["decision"] == "SIGNAL_DEDUPED"
    assert second.explain_payload["snapshot_key"] == f"KRW-BTC|1m|{second.snapshot_time.isoformat()}"
    assert second.explain_payload["matched_conditions"] == ["entry.conditions[0]"]


def test_signal_explain_includes_runtime_parameters() -> None:
    _, _, _, signal_generator = _services()
    config = _base_strategy_config()
    config["entry"] = {
        "logic": "all",
        "conditions": [
            {
                "type": "threshold_compare",
                "left": {"kind": "price", "field": "close"},
                "operator": ">",
                "right": {"kind": "constant", "value": 100.0},
            }
        ],
    }

    signal = signal_generator.evaluate(
        config,
        _snapshot(latest=110.0, open_price=100.0, high=111.0, low=99.0, close=110.0),
        "ses_test_001",
        "stv_test_001",
    )

    assert signal is not None
    assert signal.explain_payload is not None
    assert {"label": "entry.conditions[0].right.value", "value": 100.0} in signal.explain_payload["parameters"]
    assert {"label": "entry.conditions[0].right.value", "value": 100.0} in signal.explain_payload["facts"]


def test_signal_explain_includes_ema_and_breakout_facts_for_dsl_entry() -> None:
    _, _, _, signal_generator = _services()
    config = _base_strategy_config()
    config["market"] = {"timeframes": ["5m"]}
    config["entry"] = {
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
                "reference": {"kind": "derived", "name": "highest_high", "params": {"lookback": 20, "exclude_current": True}},
            },
        ],
    }

    closes = [100.0 + (index * 0.8) for index in range(59)] + [160.0]
    signal = signal_generator.evaluate(
        config,
        _snapshot_with_history(closes),
        "ses_test_001",
        "stv_test_001",
    )

    assert signal is not None
    assert signal.explain_payload is not None
    facts = signal.explain_payload["facts"]
    parameters = signal.explain_payload["parameters"]

    assert any(item["label"] == "ema20" and isinstance(item["value"], float) for item in facts)
    assert any(item["label"] == "ema50" and isinstance(item["value"], float) for item in facts)
    assert any(item["label"] == "highest_high20" and isinstance(item["value"], float) for item in facts)
    assert {"label": "entry.conditions[0].left.params.length", "value": 20} in parameters
    assert {"label": "entry.conditions[1].reference.params.lookback", "value": 20} in parameters


def test_risk_guard_max_positions_blocked() -> None:
    risk_guard = RiskGuardService()
    cfg = _base_strategy_config()
    cfg["position"] = {
        "max_open_positions_per_symbol": 1,
        "max_concurrent_positions": 1,
    }
    risk_guard.register_position("ses_test_001", "KRW-ETH", PositionState.OPEN)
    result = risk_guard.check_all(_session(), cfg, SignalAction.ENTER.value, "KRW-BTC")
    assert result.passed is False
    assert result.blocked_codes == [error_codes.RISK_MAX_CONCURRENT_POSITIONS_REACHED]


def test_existing_open_position_blocks_duplicate_entry_after_runtime_sync() -> None:
    execution, _, _, _ = _services()
    execution.sync_positions([_position(stop=95.0, tp=110.0)])

    result = execution.process_snapshot(
        _session(),
        _base_strategy_config(),
        _snapshot(latest=104.0, open_price=100.0, high=104.0, low=99.0, close=104.0),
    )

    assert result["accepted"] is False
    assert result["reason_codes"] == [error_codes.RISK_DUPLICATE_POSITION_BLOCKED]
    assert "order" not in result
    signal = result["signal"]
    assert isinstance(signal, Signal)
    assert signal.explain_payload is not None
    assert signal.explain_payload["decision"] == "EXECUTION_REJECTED"
    assert signal.explain_payload["reason_codes"] == [error_codes.RISK_DUPLICATE_POSITION_BLOCKED]


def test_reentry_cooldown_and_reset_condition_are_enforced() -> None:
    execution, _, _, _ = _services()
    config = _base_strategy_config()
    config["reentry"] = {
        "allow": True,
        "cooldown_bars": 2,
        "require_reset": True,
        "reset_condition": {
            "type": "threshold_compare",
            "left": {"kind": "price", "field": "close"},
            "operator": "<",
            "right": {"kind": "constant", "value": 105.0},
        },
    }
    execution.sync_positions([_position(stop=95.0, tp=102.0)])
    base_time = datetime.now(UTC)

    exit_result = execution.process_snapshot(
        _session(),
        config,
        _snapshot(latest=103.0, open_price=100.0, high=103.0, low=99.0, close=103.0, snapshot_time=base_time),
    )
    assert exit_result["accepted"] is True
    assert exit_result["exits"]

    cooldown_result = execution.process_snapshot(
        _session(),
        config,
        _snapshot(
            latest=110.0,
            open_price=106.0,
            high=111.0,
            low=105.0,
            close=110.0,
            snapshot_time=base_time + timedelta(seconds=1),
        ),
    )
    assert cooldown_result["accepted"] is False
    assert cooldown_result["reason_codes"] == [error_codes.RISK_REENTRY_COOLDOWN_ACTIVE]

    reset_pending_result = execution.process_snapshot(
        _session(),
        config,
        _snapshot(
            latest=109.0,
            open_price=106.0,
            high=110.0,
            low=105.0,
            close=109.0,
            snapshot_time=base_time + timedelta(seconds=2),
        ),
    )
    assert reset_pending_result["accepted"] is False
    assert reset_pending_result["reason_codes"] == [error_codes.RISK_REENTRY_RESET_PENDING]

    reentry_result = execution.process_snapshot(
        _session(),
        config,
        _snapshot(
            latest=100.0,
            open_price=100.0,
            high=101.0,
            low=99.0,
            close=100.0,
            snapshot_time=base_time + timedelta(seconds=3),
        ),
    )
    assert reentry_result["accepted"] is True
    assert isinstance(reentry_result["signal"], Signal)


def test_risk_guard_daily_loss_blocked() -> None:
    risk_guard = RiskGuardService()
    cfg = _base_strategy_config()
    risk_guard.record_daily_loss("ses_test_001", 40_000.0)
    result = risk_guard.check_all(_session(), cfg, SignalAction.ENTER.value, "KRW-BTC")
    assert result.passed is False
    assert result.blocked_codes == [error_codes.RISK_DAILY_LOSS_LIMIT_REACHED]


def test_risk_guard_kill_switch() -> None:
    risk_guard = RiskGuardService()
    risk_guard.activate_kill_switch("ses_test_001")
    result = risk_guard.check_all(_session(), _base_strategy_config(), SignalAction.ENTER.value, "KRW-BTC")
    assert result.passed is False
    assert result.blocked_codes == [error_codes.RISK_EMERGENCY_STOP_ACTIVE]


# TC-EXE-004
def test_risk_guard_mode_isolation_paper_mode_and_invalid_inputs() -> None:
    """TC-EXE-004: PAPER mode allows ENTER; invalid mode/action is blocked."""
    risk_guard = RiskGuardService()
    session = _session()
    session.mode = ExecutionMode.PAPER
    session.status = SessionStatus.RUNNING
    cfg = _base_strategy_config()

    paper_enter = risk_guard.check_all(session, cfg, SignalAction.ENTER.value, "KRW-BTC")
    assert paper_enter.passed is True

    invalid_action = risk_guard.check_all(session, cfg, "INVALID_ACTION", "KRW-BTC")
    assert invalid_action.passed is False

    session.mode = cast(ExecutionMode, "INVALID_MODE")
    invalid_mode = risk_guard.check_all(session, cfg, SignalAction.ENTER.value, "KRW-BTC")
    assert invalid_mode.passed is False


def test_slippage_fixed_bps() -> None:
    fill_engine = FillEngine()
    price = fill_engine.apply_slippage(base_price=100.0, side="BUY", model="fixed_bps", bps=50, volatility_ratio=1.0)
    assert price == pytest.approx(100.5)


def test_fee_per_fill() -> None:
    fill_engine = FillEngine()
    fee = fill_engine.calculate_fee(notional=1000.0, fee_bps=10.0, fee_model="per_fill")
    assert fee == 1.0


def test_trailing_stop() -> None:
    fill_engine = FillEngine()
    position = _position(stop=80.0, tp=200.0)
    reason = fill_engine.evaluate_exit_triggers(
        position=position,
        current_price=110.0,
        candle_high=120.0,
        candle_low=109.0,
        exit_config={"trailing_stop_pct": 0.05, "stop_loss_pct": 0.2},
        bar_count=2,
    )
    assert reason == ExitReason.TRAILING_STOP
