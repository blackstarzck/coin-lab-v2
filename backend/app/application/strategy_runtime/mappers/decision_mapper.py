from __future__ import annotations

from app.application.strategy_runtime.explain import build_explain_snapshot
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.strategy_runtime import StrategyDecisionDraft


def draft_to_strategy_decision(draft: StrategyDecisionDraft, snapshot: MarketSnapshot) -> StrategyDecision:
    explain = build_explain_snapshot(
        snapshot_key=_snapshot_key(snapshot, _draft_timeframe(draft)),
        draft=draft,
    ).to_payload()
    return StrategyDecision(
        action=PluginAction(draft.action),
        confidence=draft.confidence,
        signal_price=_signal_price(draft, snapshot),
        reason_codes=list(draft.reason_codes),
        matched_conditions=list(draft.matched_conditions),
        failed_conditions=list(draft.failed_conditions),
        facts=explain["facts"],
        parameters=explain["parameters"],
    )


def draft_to_explain_payload(
    *,
    snapshot: MarketSnapshot,
    draft: StrategyDecisionDraft,
    timeframe: str,
    fallback_decision: str | None = None,
    risk_blocks: list[str] | None = None,
) -> dict[str, object]:
    snapshot_key = _snapshot_key(snapshot, timeframe)
    explain = build_explain_snapshot(
        snapshot_key=snapshot_key,
        draft=draft,
        decision=fallback_decision if draft.action == "HOLD" and fallback_decision is not None else draft.action,
        risk_blocks=tuple(risk_blocks or ()),
    )
    return explain.to_payload()


def _signal_price(draft: StrategyDecisionDraft, snapshot: MarketSnapshot) -> float | None:
    if draft.action == "ENTER" and draft.entry_setup is not None:
        return draft.entry_setup.trigger_price
    if draft.action == "EXIT" and draft.exit_setup is not None:
        return draft.exit_setup.trigger_price
    return snapshot.latest_price


def _draft_timeframe(draft: StrategyDecisionDraft) -> str:
    if draft.entry_setup is not None:
        return draft.entry_setup.timeframe
    if draft.exit_setup is not None:
        return draft.exit_setup.timeframe
    return "1m"


def _snapshot_key(snapshot: MarketSnapshot, timeframe: str) -> str:
    return f"{snapshot.symbol}|{timeframe}|{snapshot.snapshot_time.isoformat()}"
