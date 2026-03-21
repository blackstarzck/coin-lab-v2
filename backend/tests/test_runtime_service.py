from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.application.services.execution_service import ExecutionService
from app.application.services.fill_engine import FillEngine
from app.application.services.market_ingest_service import MarketIngestService
from app.application.services.risk_guard_service import RiskGuardService
from app.application.services.runtime_service import RuntimeService
from app.application.services.signal_generator import SignalGenerator
from app.application.services.stream_service import StreamService
from app.core.config import Settings
from app.domain.entities.market import EventType, NormalizedEvent
from app.domain.entities.session import ExecutionMode, FillResult, Position, PositionState, Session, SessionStatus
from app.infrastructure.repositories.in_memory_lab_store import InMemoryLabStore


def _settings() -> Settings:
    return Settings(
        app_env="test",
        log_level="INFO",
        allowed_origins=["http://localhost:5173"],
        store_backend="memory",
        database_url=None,
        upbit_rest_base_url="https://api.upbit.com",
        upbit_ws_public_url="wss://api.upbit.com/websocket/v1",
        upbit_ws_private_url="wss://api.upbit.com/websocket/v1/private",
        upbit_access_key="access-key",
        upbit_secret_key="secret-key",
        live_trading_enabled=True,
        live_require_order_test=True,
        live_order_notional_krw=5000,
    )


def _strategy_config(trigger: str | None = None) -> dict[str, object]:
    market: dict[str, object] = {"timeframes": ["1m"]}
    if trigger is not None:
        market["trigger"] = trigger

    return {
        "market": market,
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


def _session(*, trigger: str | None = None, session_id: str = "ses_runtime_001") -> Session:
    now = datetime.now(UTC)
    return Session(
        id=session_id,
        mode=ExecutionMode.PAPER,
        status=SessionStatus.RUNNING,
        strategy_version_id="stv_runtime_001",
        symbol_scope_json={"active_symbols": ["KRW-BTC"]},
        risk_overrides_json={},
        config_snapshot=_strategy_config(trigger),
        performance_json={"initial_capital": 1_000_000, "max_drawdown_pct": 0.0},
        health_json={},
        trace_id=f"trc_{session_id}",
        started_at=now,
        ended_at=None,
        created_at=now,
        updated_at=now,
    )


def _event(dedupe_key: str, event_time: datetime, received_at: datetime) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=f"evt_{dedupe_key}",
        dedupe_key=dedupe_key,
        symbol="KRW-BTC",
        timeframe=None,
        event_type=EventType.TRADE_TICK,
        event_time=event_time,
        sequence_no=None,
        received_at=received_at,
        source="test",
        payload={"trade_price": 100.0, "trade_volume": 1.0, "acc_trade_volume_24h": 12.0},
        trace_id=f"trc_{dedupe_key}",
    )


def _runtime() -> tuple[RuntimeService, InMemoryLabStore]:
    store = InMemoryLabStore()
    stream_service = StreamService(store)
    market_ingest_service = MarketIngestService()
    risk_guard = RiskGuardService()
    fill_engine = FillEngine()
    signal_generator = SignalGenerator()
    execution_service = ExecutionService(risk_guard, fill_engine, signal_generator)
    runtime = RuntimeService(
        _settings(),
        store,
        stream_service,
        market_ingest_service,
        execution_service,
    )
    return runtime, store


def test_runtime_defaults_to_on_candle_close_and_waits_for_boundary() -> None:
    runtime, store = _runtime()
    session = _session()
    store.create_session(session)

    start = datetime.now(UTC).replace(second=10, microsecond=0)
    runtime.ingest_normalized_event(_event("same-1", start, start))
    runtime.ingest_normalized_event(_event("same-2", start + timedelta(seconds=10), start + timedelta(milliseconds=300)))

    assert store.list_session_signals(session.id) == []
    assert store.query_logs("strategy-execution", session_id=session.id, limit=20) == []

    next_batch_start = start + timedelta(seconds=40)
    runtime.ingest_normalized_event(_event("close-1", next_batch_start, next_batch_start))
    close_time = start.replace(second=0, microsecond=0) + timedelta(minutes=1)
    runtime.ingest_normalized_event(_event("close-2", close_time, next_batch_start + timedelta(milliseconds=300)))

    signals = store.list_session_signals(session.id)
    logs = store.query_logs("strategy-execution", session_id=session.id, limit=20)
    event_types = {entry.event_type for entry in logs}

    assert len(signals) == 1
    assert signals[0].snapshot_time == close_time
    assert "EVALUATION_STARTED" in event_types
    assert "SIGNAL_EMITTED" in event_types
    assert "EVALUATION_COMPLETED" in event_types
    assert "SIGNAL_EVALUATED" not in event_types


def test_runtime_respects_explicit_on_tick_batch_trigger() -> None:
    runtime, store = _runtime()
    session = _session(trigger="ON_TICK_BATCH", session_id="ses_runtime_tick")
    store.create_session(session)

    start = datetime.now(UTC).replace(microsecond=0)
    runtime.ingest_normalized_event(_event("tick-1", start, start))
    runtime.ingest_normalized_event(_event("tick-2", start + timedelta(seconds=5), start + timedelta(milliseconds=300)))

    signals = store.list_session_signals(session.id)
    logs = store.query_logs("strategy-execution", session_id=session.id, limit=20)
    event_types = {entry.event_type for entry in logs}

    assert len(signals) == 1
    assert signals[0].snapshot_time == start + timedelta(seconds=5)
    assert "EVALUATION_STARTED" in event_types
    assert "SIGNAL_EMITTED" in event_types
    assert "EVALUATION_COMPLETED" in event_types


def test_runtime_skips_stale_snapshot_execution_and_logs_reason() -> None:
    runtime, store = _runtime()
    session = _session(trigger="ON_TICK_BATCH", session_id="ses_runtime_stale")
    store.create_session(session)

    old_start = datetime.now(UTC) - timedelta(seconds=5)
    runtime.ingest_normalized_event(_event("stale-1", old_start, old_start))
    runtime.ingest_normalized_event(_event("stale-2", old_start + timedelta(milliseconds=300), old_start + timedelta(milliseconds=300)))

    signals = store.list_session_signals(session.id)
    logs = store.query_logs("strategy-execution", session_id=session.id, limit=20)
    skip_logs = [entry for entry in logs if entry.event_type == "EVALUATION_SKIPPED"]

    assert signals == []
    assert len(skip_logs) == 1
    assert skip_logs[0].payload["reason_code"] == "EXEC_SNAPSHOT_STALE"


def test_manual_reevaluate_uses_manual_trigger_and_selected_symbols() -> None:
    runtime, store = _runtime()
    session = _session(session_id="ses_runtime_manual")
    session.symbol_scope_json["active_symbols"] = ["KRW-BTC", "KRW-ETH"]
    store.create_session(session)

    btc_time = datetime.now(UTC).replace(microsecond=0)
    eth_time = btc_time + timedelta(milliseconds=10)
    runtime.ingest_normalized_event(_event("manual-btc-1", btc_time, btc_time))
    runtime.ingest_normalized_event(_event("manual-btc-2", btc_time + timedelta(milliseconds=300), btc_time + timedelta(milliseconds=300)))
    runtime.ingest_normalized_event(
        NormalizedEvent(
            event_id="evt_manual_eth_1",
            dedupe_key="manual-eth-1",
            symbol="KRW-ETH",
            timeframe=None,
            event_type=EventType.TRADE_TICK,
            event_time=eth_time,
            sequence_no=None,
            received_at=eth_time,
            source="test",
            payload={"trade_price": 200.0, "trade_volume": 1.0, "acc_trade_volume_24h": 8.0},
            trace_id="trc_manual_eth_1",
        )
    )
    runtime.ingest_normalized_event(
        NormalizedEvent(
            event_id="evt_manual_eth_2",
            dedupe_key="manual-eth-2",
            symbol="KRW-ETH",
            timeframe=None,
            event_type=EventType.TRADE_TICK,
            event_time=eth_time + timedelta(milliseconds=300),
            sequence_no=None,
            received_at=eth_time + timedelta(milliseconds=300),
            source="test",
            payload={"trade_price": 201.0, "trade_volume": 1.0, "acc_trade_volume_24h": 8.0},
            trace_id="trc_manual_eth_2",
        )
    )

    result = runtime.manual_reevaluate_session(session, ["KRW-BTC"])
    logs = store.query_logs("strategy-execution", session_id=session.id, limit=20)
    manual_logs = [entry for entry in logs if entry.payload.get("trigger") == "ON_MANUAL_REEVALUATE"]
    btc_logs = [entry for entry in logs if entry.symbol == "KRW-BTC"]

    assert result["accepted"] is True
    assert result["requested_symbols"] == ["KRW-BTC"]
    assert result["evaluated_symbols"] == ["KRW-BTC"]
    assert all(entry.symbol == "KRW-BTC" for entry in manual_logs)
    assert {entry.event_type for entry in manual_logs} == {"EVALUATION_STARTED", "EVALUATION_COMPLETED"}
    assert "SIGNAL_EMITTED" in {entry.event_type for entry in btc_logs}
    refreshed_session = store.get_session(session.id)
    assert refreshed_session is not None
    assert refreshed_session.health_json["snapshot_consistency"] == "HEALTHY"


def test_runtime_records_realized_pnl_for_closed_position_with_exit_fill_qty() -> None:
    runtime, store = _runtime()
    session = _session(session_id="ses_runtime_realized")
    store.create_session(session)

    closed_position = Position(
        id="pos_runtime_closed",
        session_id=session.id,
        strategy_version_id=session.strategy_version_id,
        symbol="KRW-BTC",
        position_state=PositionState.CLOSED,
        side="BUY",
        entry_time=datetime.now(UTC) - timedelta(hours=1),
        avg_entry_price=100.0,
        quantity=0.0,
        stop_loss_price=95.0,
        take_profit_price=110.0,
        unrealized_pnl=0.0,
        unrealized_pnl_pct=0.0,
    )

    runtime._persist_execution_result(  # noqa: SLF001 - regression coverage for monitoring PnL aggregation
        session,
        snapshot=type("Snapshot", (), {"symbol": "KRW-BTC"})(),
        result={
            "exits": [
                {
                    "position": closed_position,
                    "fill": FillResult(
                        filled=True,
                        fill_price=110.0,
                        fill_qty=2.0,
                        fee_amount=0.0,
                        slippage_amount=0.0,
                    ),
                    "exit_reason": "TAKE_PROFIT",
                }
            ]
        },
    )

    refreshed_session = store.get_session(session.id)
    assert refreshed_session is not None
    assert refreshed_session.performance_json["realized_pnl"] == 20.0
    assert refreshed_session.performance_json["trade_count"] == 1
    assert refreshed_session.performance_json["winning_trade_count"] == 1
    assert refreshed_session.performance_json["symbol_performance"]["KRW-BTC"]["realized_pnl"] == 20.0
    assert refreshed_session.performance_json["symbol_performance"]["KRW-BTC"]["realized_pnl_pct"] == 10.0


def test_runtime_reports_worker_state_and_last_event_timestamp() -> None:
    runtime, _store = _runtime()
    event_time = datetime.now(UTC).replace(microsecond=0)
    runtime._last_runtime_event_at = event_time  # noqa: SLF001 - status regression coverage

    status = runtime.status()

    assert status["worker_alive"] is False
    assert status["last_runtime_event_at"] == event_time


def test_runtime_reconnects_when_connection_is_idle() -> None:
    runtime, _store = _runtime()
    runtime._last_runtime_event_at = datetime.now(UTC) - timedelta(seconds=runtime.IDLE_RECONNECT_TIMEOUT_SECONDS + 1)  # noqa: SLF001

    assert runtime._should_reconnect_on_idle(datetime.now(UTC)) is True  # noqa: SLF001


def test_runtime_does_not_reconnect_when_recent_event_exists() -> None:
    runtime, _store = _runtime()
    runtime._last_runtime_event_at = datetime.now(UTC) - timedelta(seconds=runtime.IDLE_RECONNECT_TIMEOUT_SECONDS - 2)  # noqa: SLF001

    assert runtime._should_reconnect_on_idle(datetime.now(UTC)) is False  # noqa: SLF001


def test_runtime_refresh_gate_uses_wall_clock_for_manual_snapshots() -> None:
    runtime, _store = _runtime()
    session_id = "ses_refresh_gate"
    runtime._last_session_refresh_at[session_id] = datetime.now(UTC) - timedelta(seconds=5)  # noqa: SLF001
    old_snapshot_time = datetime.now(UTC) - timedelta(minutes=10)

    assert runtime._should_refresh_session_state(session_id, old_snapshot_time) is True  # noqa: SLF001
