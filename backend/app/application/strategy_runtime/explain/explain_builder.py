from __future__ import annotations

from app.domain.strategy_runtime import EntrySetup, ExitSetup, ExplainItem, ExplainSnapshot, StrategyDecisionDraft


def build_explain_snapshot(
    *,
    snapshot_key: str,
    draft: StrategyDecisionDraft,
    decision: str | None = None,
    risk_blocks: tuple[str, ...] = (),
    execution_facts: tuple[ExplainItem, ...] = (),
) -> ExplainSnapshot:
    return ExplainSnapshot(
        snapshot_key=snapshot_key,
        decision=decision or draft.action,
        detector_facts=draft.facts,
        setup_facts=_setup_facts(draft),
        execution_facts=execution_facts,
        parameters=_parameters(draft),
        matched_conditions=draft.matched_conditions,
        failed_conditions=draft.failed_conditions,
        reason_codes=draft.reason_codes,
        risk_blocks=risk_blocks,
        runtime_context=_runtime_context(draft),
    )


def _setup_facts(draft: StrategyDecisionDraft) -> tuple[ExplainItem, ...]:
    facts: list[ExplainItem] = []
    if draft.entry_setup is not None:
        facts.extend(draft.entry_setup.facts)
        facts.extend(draft.entry_setup.confluence.facts)
    if draft.exit_setup is not None:
        facts.extend(draft.exit_setup.facts)
    return tuple(facts)


def _parameters(draft: StrategyDecisionDraft) -> tuple[ExplainItem, ...]:
    params: list[ExplainItem] = list(draft.parameters)
    if draft.entry_setup is not None:
        params.extend(draft.entry_setup.parameters)
    if draft.exit_setup is not None:
        params.extend(draft.exit_setup.parameters)
    return tuple(params)


def _runtime_context(draft: StrategyDecisionDraft) -> dict[str, object]:
    return {
        "entry_setup": None if draft.entry_setup is None else _serialize_entry_setup(draft.entry_setup),
        "exit_setup": None if draft.exit_setup is None else _serialize_exit_setup(draft.exit_setup),
    }


def _serialize_entry_setup(setup: EntrySetup) -> dict[str, object]:
    return {
        "setup_id": setup.setup_id,
        "symbol": setup.symbol,
        "timeframe": setup.timeframe,
        "direction": setup.direction,
        "setup_type": setup.setup_type,
        "valid": setup.valid,
        "confidence": setup.confidence,
        "trigger_price": setup.trigger_price,
        "preferred_entry_zone": list(setup.preferred_entry_zone) if setup.preferred_entry_zone is not None else None,
        "invalidation_price": setup.invalidation_price,
        "reason_codes": list(setup.reason_codes),
        "confluence": {
            "score": setup.confluence.score,
            "max_score": setup.confluence.max_score,
            "matched_conditions": list(setup.confluence.matched_conditions),
            "failed_conditions": list(setup.confluence.failed_conditions),
            "reason_codes": list(setup.confluence.reason_codes),
        },
        "risk": {
            "invalidation_price": setup.risk.invalidation_price,
            "stop_loss_price": setup.risk.stop_loss_price,
            "take_profit_prices": list(setup.risk.take_profit_prices),
            "trailing_activation_price": setup.risk.trailing_activation_price,
            "max_holding_bars": setup.risk.max_holding_bars,
        },
    }


def _serialize_exit_setup(setup: ExitSetup) -> dict[str, object]:
    return {
        "setup_id": setup.setup_id,
        "symbol": setup.symbol,
        "timeframe": setup.timeframe,
        "exit_type": setup.exit_type,
        "valid": setup.valid,
        "priority": setup.priority,
        "trigger_price": setup.trigger_price,
        "invalidation_price": setup.invalidation_price,
        "reason_codes": list(setup.reason_codes),
    }
