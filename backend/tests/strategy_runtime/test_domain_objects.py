from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pytest

from app.domain.strategy_runtime import (
    DetectorResult,
    EntrySetup,
    ExecutionEnvelope,
    ExecutionOutcomeDraft,
    ExitPlan,
    ExplainItem,
    ExplainSnapshot,
    FairValueGapZone,
    OrderIntentPlan,
    RiskEnvelope,
    SetupConfluence,
    TrendContext,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _trend_context() -> TrendContext:
    now = _now()
    return TrendContext(
        structure_id="trend_ctx_001",
        kind="trend_context",
        symbol="KRW-BTC",
        timeframe="5m",
        direction="bullish",
        formed_at=now,
        invalidated_at=None,
        confidence=0.8,
        support=100.0,
        resistance=112.0,
        average_close=106.5,
        start_close=101.0,
        latest_close=111.0,
        trend_state="trend_up",
        facts=(ExplainItem(label="detector.trend_context.latest_close", value=111.0),),
        reason_codes=("DETECTOR_MATCHED",),
    )


def _fvg_zone() -> FairValueGapZone:
    now = _now()
    return FairValueGapZone(
        structure_id="fvg_001",
        kind="fair_value_gap",
        symbol="KRW-BTC",
        timeframe="5m",
        direction="bullish",
        formed_at=now,
        invalidated_at=None,
        confidence=0.75,
        lower=104.0,
        upper=106.0,
        midpoint=105.0,
        invalidation_price=103.5,
        retested=True,
        active=True,
        left_candle_at=now,
        middle_candle_at=now,
        right_candle_at=now,
        gap_pct=0.012,
    )


def test_detector_result_rejects_matched_when_not_ready() -> None:
    with pytest.raises(ValueError, match="matched cannot be true when ready is false"):
        DetectorResult[TrendContext](
            detector_id="trend_context",
            ready=False,
            matched=True,
        )


def test_detector_result_rejects_primary_not_in_items() -> None:
    with pytest.raises(ValueError, match="primary must be one of the detector result items"):
        DetectorResult[TrendContext](
            detector_id="trend_context",
            ready=True,
            matched=True,
            items=(),
            primary=_trend_context(),
        )


def test_explain_snapshot_to_payload_flattens_all_fact_groups() -> None:
    snapshot = ExplainSnapshot(
        snapshot_key="KRW-BTC|5m|2026-03-19T00:00:00+00:00",
        decision="ENTER",
        detector_facts=(ExplainItem(label="detector.fvg.lower", value=104.0),),
        setup_facts=(ExplainItem(label="composer.entry_setup.score", value=3),),
        execution_facts=(ExplainItem(label="execution.entry_policy.timeout_sec", value=15),),
        parameters=(ExplainItem(label="execution.sizing_policy.mode", value="fixed_percent"),),
        matched_conditions=("entry.fvg_retest",),
        failed_conditions=(),
        reason_codes=("PLUGIN_SMC_CONFLUENCE_ENTRY",),
        risk_blocks=(),
    )

    payload = snapshot.to_payload()

    assert payload["snapshot_key"] == "KRW-BTC|5m|2026-03-19T00:00:00+00:00"
    assert payload["decision"] == "ENTER"
    assert payload["reason_codes"] == ["PLUGIN_SMC_CONFLUENCE_ENTRY"]
    assert payload["matched_conditions"] == ["entry.fvg_retest"]
    assert payload["facts"] == [
        {"label": "detector.fvg.lower", "value": 104.0},
        {"label": "composer.entry_setup.score", "value": 3},
        {"label": "execution.entry_policy.timeout_sec", "value": 15},
    ]
    assert payload["parameters"] == [{"label": "execution.sizing_policy.mode", "value": "fixed_percent"}]


def test_nested_strategy_runtime_objects_are_dataclass_serializable() -> None:
    trend = _trend_context()
    fvg = _fvg_zone()
    confluence = SetupConfluence(
        score=3,
        max_score=4,
        matched_conditions=("trend_up", "fvg_retested"),
        failed_conditions=("order_block_missing",),
    )
    risk = RiskEnvelope(
        invalidation_price=103.5,
        stop_loss_price=103.0,
        take_profit_prices=(108.0, 110.0),
        trailing_activation_price=108.5,
        max_holding_bars=12,
    )
    entry_setup = EntrySetup(
        setup_id="entry_001",
        symbol="KRW-BTC",
        timeframe="5m",
        direction="long",
        setup_type="fvg_retest_long",
        valid=True,
        confidence=0.75,
        trigger_price=106.0,
        preferred_entry_zone=(104.0, 106.0),
        invalidation_price=103.5,
        confluence=confluence,
        risk=risk,
        structures=(trend, fvg),
        facts=(ExplainItem(label="composer.entry_setup.zone_midpoint", value=105.0),),
    )
    order_intent = OrderIntentPlan(
        symbol="KRW-BTC",
        side="BUY",
        order_role="ENTRY",
        order_type="LIMIT",
        requested_qty=0.25,
        requested_price=105.0,
        timeout_sec=15.0,
        fallback_to_market=True,
        retries_allowed=2,
    )
    exit_plan = ExitPlan(
        exit_type="zone_invalidation",
        order_type="MARKET",
        trigger_price=103.5,
        close_ratio=1.0,
        priority=1,
        fallback_to_market=True,
    )
    envelope = ExecutionEnvelope(
        entry_intent=order_intent,
        position_plan=None,
        exit_plans=(exit_plan,),
        reason_codes=("EXECUTION_PLAN_READY",),
    )
    outcome = ExecutionOutcomeDraft(
        accepted=True,
        order_intent=order_intent,
        fill_price=105.0,
        fill_qty=0.25,
        resulting_position_state="OPEN",
        explain_snapshot=ExplainSnapshot(
            snapshot_key="KRW-BTC|5m|2026-03-19T00:00:00+00:00",
            decision="ENTER",
            detector_facts=(ExplainItem(label="detector.trend_context.latest_close", value=111.0),),
            setup_facts=(ExplainItem(label="composer.entry_setup.valid", value=True),),
            execution_facts=(ExplainItem(label="execution.entry_policy.order_type", value="LIMIT"),),
            parameters=(ExplainItem(label="execution.entry_policy.timeout_sec", value=15),),
            matched_conditions=("entry.fvg_retest",),
            failed_conditions=(),
            reason_codes=("ENTRY_ACCEPTED",),
            risk_blocks=(),
        ),
        reason_codes=("ENTRY_ACCEPTED",),
    )

    entry_dict = asdict(entry_setup)
    envelope_dict = asdict(envelope)
    outcome_payload = outcome.to_payload()

    assert entry_dict["setup_type"] == "fvg_retest_long"
    assert entry_dict["confluence"]["score"] == 3
    assert entry_dict["risk"]["take_profit_prices"] == (108.0, 110.0)
    assert entry_dict["structures"][0]["trend_state"] == "trend_up"
    assert envelope_dict["entry_intent"]["order_type"] == "LIMIT"
    assert envelope_dict["exit_plans"][0]["exit_type"] == "zone_invalidation"
    assert outcome_payload["accepted"] is True
    assert outcome_payload["fill_price"] == 105.0
    assert isinstance(outcome_payload["explain_snapshot"], dict)
