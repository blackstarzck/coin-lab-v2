from __future__ import annotations

from dataclasses import dataclass

from .execution_plans import OrderIntentPlan
from .market_structures import ExplainItem, ExplainScalar, serialize_explain_items


@dataclass(slots=True, kw_only=True)
class ExplainSnapshot:
    snapshot_key: str
    decision: str
    detector_facts: tuple[ExplainItem, ...] = ()
    setup_facts: tuple[ExplainItem, ...] = ()
    execution_facts: tuple[ExplainItem, ...] = ()
    parameters: tuple[ExplainItem, ...] = ()
    matched_conditions: tuple[str, ...] = ()
    failed_conditions: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    risk_blocks: tuple[str, ...] = ()
    runtime_context: dict[str, object] | None = None

    def all_facts(self) -> tuple[ExplainItem, ...]:
        return (*self.detector_facts, *self.setup_facts, *self.execution_facts)

    def to_payload(self) -> dict[str, object]:
        facts = serialize_explain_items(self.all_facts())
        parameters = serialize_explain_items(self.parameters)
        payload = {
            "snapshot_key": self.snapshot_key,
            "decision": self.decision,
            "reason_codes": list(self.reason_codes),
            "facts": facts,
            "parameters": parameters,
            "matched_conditions": list(self.matched_conditions),
            "failed_conditions": list(self.failed_conditions),
            "risk_blocks": list(self.risk_blocks),
        }
        if self.runtime_context is not None:
            payload["strategy_runtime"] = self.runtime_context
        return payload


@dataclass(slots=True, kw_only=True)
class ExecutionOutcomeDraft:
    accepted: bool
    order_intent: OrderIntentPlan | None
    fill_price: float | None
    fill_qty: float
    resulting_position_state: str | None
    explain_snapshot: ExplainSnapshot | None
    reason_codes: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, ExplainScalar | dict[str, object] | None]:
        return {
            "accepted": self.accepted,
            "fill_price": self.fill_price,
            "fill_qty": self.fill_qty,
            "resulting_position_state": self.resulting_position_state,
            "explain_snapshot": None if self.explain_snapshot is None else self.explain_snapshot.to_payload(),
        }
