from __future__ import annotations

from app.domain.entities.market import MarketSnapshot
from app.domain.entities.session import OrderIntent, OrderRole, OrderType, Session, Signal
from app.domain.strategy_runtime import OrderIntentPlan


class EntryExecutionPolicy:
    def build_plan(
        self,
        *,
        signal: Signal,
        session: Session,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        requested_qty: float,
    ) -> OrderIntentPlan:
        execution_cfg = self._as_dict(strategy_config.get("execution"))
        modules_cfg = self._as_dict(strategy_config.get("execution_modules"))
        entry_cfg = self._as_dict(modules_cfg.get("entry_policy"))
        order_type = str(entry_cfg.get("order_type", execution_cfg.get("entry_order_type", OrderType.MARKET.value))).upper()
        timeout_sec = self._as_float(entry_cfg.get("timeout_sec", execution_cfg.get("limit_timeout_sec")), 15.0)
        fallback_to_market = bool(entry_cfg.get("fallback_to_market", execution_cfg.get("fallback_to_market", True)))
        limit_price = self._resolve_limit_price(signal, snapshot, entry_cfg, order_type)
        return OrderIntentPlan(
            symbol=signal.symbol,
            side="BUY",
            order_role=OrderRole.ENTRY.value,
            order_type=order_type,
            requested_qty=requested_qty,
            requested_price=limit_price,
            timeout_sec=timeout_sec,
            fallback_to_market=fallback_to_market,
            retries_allowed=self._as_int(self._as_dict(strategy_config.get("risk")).get("max_order_retries"), 0),
        )

    def to_order_intent(self, *, signal: Signal, session: Session, plan: OrderIntentPlan) -> OrderIntent:
        return OrderIntent(
            signal_id=signal.id,
            session_id=session.id,
            symbol=plan.symbol,
            side=plan.side,
            order_type=plan.order_type,
            order_role=plan.order_role,
            requested_qty=plan.requested_qty,
            limit_price=plan.requested_price,
            timeout_sec=plan.timeout_sec or 15.0,
            fallback_to_market=plan.fallback_to_market,
            idempotency_key=f"{session.id}:{signal.id}:{signal.symbol}:{signal.snapshot_time.isoformat()}",
            trace_id=session.trace_id,
        )

    def _resolve_limit_price(
        self,
        signal: Signal,
        snapshot: MarketSnapshot,
        entry_cfg: dict[str, object],
        order_type: str,
    ) -> float | None:
        if order_type != OrderType.LIMIT.value:
            return None
        policy_id = str(entry_cfg.get("policy_id", "signal_price"))
        runtime = self._runtime_context(signal)
        entry_setup = runtime.get("entry_setup")
        if policy_id == "setup_zone_limit_v1" and isinstance(entry_setup, dict):
            zone = entry_setup.get("preferred_entry_zone")
            if isinstance(zone, list) and len(zone) == 2 and all(isinstance(item, int | float) for item in zone):
                return (float(zone[0]) + float(zone[1])) / 2.0
            trigger_price = entry_setup.get("trigger_price")
            if isinstance(trigger_price, int | float):
                return float(trigger_price)
        return signal.signal_price if signal.signal_price is not None else snapshot.latest_price

    def _runtime_context(self, signal: Signal) -> dict[str, object]:
        runtime = signal.explain_payload.get("strategy_runtime") if isinstance(signal.explain_payload, dict) else None
        return runtime if isinstance(runtime, dict) else {}

    def _as_dict(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    def _as_float(self, value: object, fallback: float) -> float:
        return float(value) if isinstance(value, int | float) else fallback

    def _as_int(self, value: object, fallback: int) -> int:
        return int(value) if isinstance(value, int | float) else fallback
