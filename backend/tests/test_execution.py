from __future__ import annotations

from datetime import UTC, datetime
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


def _snapshot(*, latest: float, open_price: float, high: float, low: float, close: float) -> MarketSnapshot:
    now = datetime.now(UTC)
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
        _snapshot(latest=110.0, open_price=100.0, high=112.0, low=99.0, close=111.0),
    )

    assert result["accepted"] is False
    assert result["reason_codes"] == [error_codes.RISK_DUPLICATE_POSITION_BLOCKED]
    assert "order" not in result


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
