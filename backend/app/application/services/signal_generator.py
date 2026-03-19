from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ...core import error_codes
from ...core.logging import get_logger
from ...application.strategy_runtime import HybridStrategyRuntime
from ...domain.entities.market import MarketSnapshot
from ...domain.entities.strategy_decision import PluginAction, StrategyDecision
from ...domain.entities.session import Signal, SignalAction
from .strategy_runtime_evaluator import EvaluationResult, StrategyRuntimeEvaluator
from .strategy_plugin_registry import StrategyPluginRegistry

logger = get_logger(__name__)


class SignalGenerator:
    def __init__(
        self,
        runtime_evaluator: StrategyRuntimeEvaluator | None = None,
        plugin_registry: StrategyPluginRegistry | None = None,
        hybrid_runtime: HybridStrategyRuntime | None = None,
    ) -> None:
        self.runtime_evaluator = runtime_evaluator or StrategyRuntimeEvaluator()
        self.plugin_registry = plugin_registry or StrategyPluginRegistry()
        self.hybrid_runtime = hybrid_runtime or HybridStrategyRuntime()
        self._signal_dedupe: dict[str, datetime] = {}

    def evaluate(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        session_id: str,
        strategy_version_id: str,
    ) -> Signal | None:
        strategy_type = str(strategy_config.get("type", "dsl"))
        if strategy_type == "plugin":
            return self._evaluate_plugin_entry(strategy_config, snapshot, session_id, strategy_version_id)
        if strategy_type == "hybrid":
            return self._evaluate_hybrid_entry(strategy_config, snapshot, session_id, strategy_version_id)

        entry_node = strategy_config.get("entry")
        if not isinstance(entry_node, dict):
            return None

        timeframe = self.primary_timeframe(strategy_config)
        snapshot_key = self.snapshot_key(snapshot, timeframe)
        evaluation = self.runtime_evaluator.evaluate(entry_node, snapshot, path="entry", default_timeframe=timeframe)
        if not evaluation.matched:
            logger.debug("Signal conditions not met", extra={"session_id": session_id, "symbol": snapshot.symbol})
            return None

        action = SignalAction.ENTER.value
        explain_payload = self.runtime_evaluator.build_explain_payload(
            snapshot_key=snapshot_key,
            decision=action,
            result=evaluation,
        )
        dedupe_key = self._generate_signal_dedupe_key(
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            snapshot_key=snapshot_key,
        )

        if self._is_duplicate_signal(dedupe_key):
            logger.info(
                "Duplicate signal rejected",
                extra={"error_code": error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED, "session_id": session_id, "symbol": snapshot.symbol},
            )
            return Signal(
                id=f"sig_{uuid4().hex[:12]}",
                session_id=session_id,
                strategy_version_id=strategy_version_id,
                symbol=snapshot.symbol,
                timeframe=timeframe,
                action=action,
                signal_price=snapshot.latest_price,
                confidence=1.0,
                reason_codes=[error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED],
                snapshot_time=snapshot.snapshot_time,
                blocked=True,
                explain_payload=self.runtime_evaluator.build_explain_payload(
                    snapshot_key=snapshot_key,
                    decision="SIGNAL_DEDUPED",
                    result=evaluation,
                    risk_blocks=[error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED],
                ),
            )

        self._signal_dedupe[dedupe_key] = datetime.now(UTC)
        logger.info("Signal generated", extra={"session_id": session_id, "symbol": snapshot.symbol, "reason_codes": evaluation.reason_codes})
        return Signal(
            id=f"sig_{uuid4().hex[:12]}",
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            signal_price=snapshot.latest_price,
            confidence=1.0,
            reason_codes=evaluation.reason_codes or ["ENTRY_CONDITION_MET"],
            snapshot_time=snapshot.snapshot_time,
            blocked=False,
            explain_payload=explain_payload,
        )

    def evaluate_plugin_decision(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> StrategyDecision | None:
        plugin_id = strategy_config.get("plugin_id")
        plugin = self.plugin_registry.get(str(plugin_id) if isinstance(plugin_id, str) else None)
        if plugin is None:
            logger.error(
                "Strategy plugin not found",
                extra={"error_code": error_codes.DSL_PLUGIN_LOAD_FAILED, "plugin_id": plugin_id, "symbol": snapshot.symbol},
            )
            return None

        plugin_config = strategy_config.get("plugin_config")
        try:
            return plugin.evaluate(snapshot, plugin_config if isinstance(plugin_config, dict) else {})
        except ValueError:
            logger.exception(
                "Strategy plugin config is invalid at runtime",
                extra={"error_code": error_codes.DSL_PLUGIN_CONTRACT_INVALID, "plugin_id": plugin.plugin_id, "symbol": snapshot.symbol},
            )
            return None
        except Exception:
            logger.exception(
                "Strategy plugin evaluation failed",
                extra={"error_code": error_codes.DSL_PLUGIN_LOAD_FAILED, "plugin_id": plugin.plugin_id, "symbol": snapshot.symbol},
            )
            return None

    def evaluate_hybrid_decision(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
    ) -> StrategyDecision | None:
        try:
            return self.hybrid_runtime.evaluate(strategy_config, snapshot)
        except ValueError:
            logger.exception(
                "Strategy hybrid config is invalid at runtime",
                extra={"error_code": error_codes.DSL_PLUGIN_CONTRACT_INVALID, "symbol": snapshot.symbol},
            )
            return None
        except Exception:
            logger.exception(
                "Strategy hybrid evaluation failed",
                extra={"error_code": error_codes.DSL_PLUGIN_LOAD_FAILED, "symbol": snapshot.symbol},
            )
            return None

    def evaluate_block(
        self,
        node: dict[str, object],
        snapshot: MarketSnapshot,
        *,
        path: str,
        default_timeframe: str,
    ) -> EvaluationResult:
        return self.runtime_evaluator.evaluate(node, snapshot, path=path, default_timeframe=default_timeframe)

    def build_explain_payload(
        self,
        *,
        snapshot_key: str,
        decision: str,
        result: EvaluationResult,
        risk_blocks: list[str] | None = None,
    ) -> dict[str, object]:
        return self.runtime_evaluator.build_explain_payload(
            snapshot_key=snapshot_key,
            decision=decision,
            result=result,
            risk_blocks=risk_blocks,
        )

    def build_plugin_explain_payload(
        self,
        *,
        snapshot_key: str,
        decision: StrategyDecision,
        fallback_decision: str,
        risk_blocks: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "snapshot_key": snapshot_key,
            "decision": decision.action.value if decision.action != PluginAction.HOLD else fallback_decision,
            "reason_codes": decision.reason_codes,
            "facts": decision.facts,
            "parameters": decision.parameters,
            "matched_conditions": decision.matched_conditions,
            "failed_conditions": decision.failed_conditions,
            "risk_blocks": risk_blocks or [],
            "legacy_payload": False,
            "legacy_note": None,
        }

    def explain_plugin_strategy(
        self,
        *,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        fallback_decision: str,
        risk_blocks: list[str] | None = None,
    ) -> dict[str, object]:
        plugin_id = strategy_config.get("plugin_id")
        plugin = self.plugin_registry.get(str(plugin_id) if isinstance(plugin_id, str) else None)
        if plugin is None:
            return {
                "snapshot_key": self.snapshot_key(snapshot, self.primary_timeframe(strategy_config)),
                "decision": fallback_decision,
                "reason_codes": [error_codes.DSL_PLUGIN_LOAD_FAILED],
                "facts": [],
                "parameters": [],
                "matched_conditions": [],
                "failed_conditions": [],
                "risk_blocks": list(risk_blocks or []),
            }
        payload = plugin.explain(snapshot, self._plugin_config(strategy_config))
        payload = dict(payload)
        payload.setdefault("snapshot_key", self.snapshot_key(snapshot, self.primary_timeframe(strategy_config)))
        if payload.get("decision") == PluginAction.HOLD.value:
            payload["decision"] = fallback_decision
        payload["risk_blocks"] = list(risk_blocks or [])
        payload.setdefault("legacy_payload", False)
        payload.setdefault("legacy_note", None)
        return payload

    def build_hybrid_explain_payload(
        self,
        *,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        fallback_decision: str,
        risk_blocks: list[str] | None = None,
    ) -> dict[str, object]:
        return self.hybrid_runtime.explain(
            strategy_config,
            snapshot,
            fallback_decision=fallback_decision,
            risk_blocks=risk_blocks,
        )

    def snapshot_key(self, snapshot: MarketSnapshot, timeframe: str) -> str:
        return f"{snapshot.symbol}|{timeframe}|{snapshot.snapshot_time.isoformat()}"

    def primary_timeframe(self, strategy_config: dict[str, object]) -> str:
        market = strategy_config.get("market")
        timeframes = market.get("timeframes") if isinstance(market, dict) and isinstance(market.get("timeframes"), list) else []
        return str(timeframes[0]) if timeframes else "1m"

    def _generate_signal_dedupe_key(
        self,
        session_id: str,
        strategy_version_id: str,
        symbol: str,
        timeframe: str,
        action: str,
        snapshot_key: str,
    ) -> str:
        return "|".join([session_id, strategy_version_id, symbol, timeframe, action, snapshot_key])

    def _is_duplicate_signal(self, dedupe_key: str) -> bool:
        now = datetime.now(UTC)
        expiry = timedelta(minutes=5)
        expired_keys = [key for key, ts in self._signal_dedupe.items() if now - ts > expiry]
        for key in expired_keys:
            del self._signal_dedupe[key]
        return dedupe_key in self._signal_dedupe

    def _evaluate_plugin_entry(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        session_id: str,
        strategy_version_id: str,
    ) -> Signal | None:
        timeframe = self.primary_timeframe(strategy_config)
        snapshot_key = self.snapshot_key(snapshot, timeframe)
        decision = self.evaluate_plugin_decision(strategy_config, snapshot)
        if decision is None or decision.action != PluginAction.ENTER:
            logger.debug("Plugin entry conditions not met", extra={"session_id": session_id, "symbol": snapshot.symbol})
            return None

        action = SignalAction.ENTER.value
        dedupe_key = self._generate_signal_dedupe_key(
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            snapshot_key=snapshot_key,
        )
        explain_payload = self.explain_plugin_strategy(strategy_config=strategy_config, snapshot=snapshot, fallback_decision=action)

        if self._is_duplicate_signal(dedupe_key):
            logger.info(
                "Duplicate plugin signal rejected",
                extra={"error_code": error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED, "session_id": session_id, "symbol": snapshot.symbol},
            )
            return Signal(
                id=f"sig_{uuid4().hex[:12]}",
                session_id=session_id,
                strategy_version_id=strategy_version_id,
                symbol=snapshot.symbol,
                timeframe=timeframe,
                action=action,
                signal_price=decision.signal_price if decision.signal_price is not None else snapshot.latest_price,
                confidence=decision.confidence,
                reason_codes=[error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED],
                snapshot_time=snapshot.snapshot_time,
                blocked=True,
                explain_payload=self.explain_plugin_strategy(
                    strategy_config=strategy_config,
                    snapshot=snapshot,
                    fallback_decision="SIGNAL_DEDUPED",
                    risk_blocks=[error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED],
                ),
            )

        self._signal_dedupe[dedupe_key] = datetime.now(UTC)
        logger.info("Plugin signal generated", extra={"session_id": session_id, "symbol": snapshot.symbol, "reason_codes": decision.reason_codes})
        return Signal(
            id=f"sig_{uuid4().hex[:12]}",
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            signal_price=decision.signal_price if decision.signal_price is not None else snapshot.latest_price,
            confidence=decision.confidence,
            reason_codes=decision.reason_codes or ["PLUGIN_ENTRY_CONDITION_MET"],
            snapshot_time=snapshot.snapshot_time,
            blocked=False,
            explain_payload=explain_payload,
        )

    def _evaluate_hybrid_entry(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        session_id: str,
        strategy_version_id: str,
    ) -> Signal | None:
        timeframe = self.primary_timeframe(strategy_config)
        snapshot_key = self.snapshot_key(snapshot, timeframe)
        decision = self.evaluate_hybrid_decision(strategy_config, snapshot)
        if decision is None or decision.action != PluginAction.ENTER:
            logger.debug("Hybrid entry conditions not met", extra={"session_id": session_id, "symbol": snapshot.symbol})
            return None

        action = SignalAction.ENTER.value
        dedupe_key = self._generate_signal_dedupe_key(
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            snapshot_key=snapshot_key,
        )
        explain_payload = self.build_hybrid_explain_payload(
            strategy_config=strategy_config,
            snapshot=snapshot,
            fallback_decision=action,
        )

        if self._is_duplicate_signal(dedupe_key):
            logger.info(
                "Duplicate hybrid signal rejected",
                extra={"error_code": error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED, "session_id": session_id, "symbol": snapshot.symbol},
            )
            return Signal(
                id=f"sig_{uuid4().hex[:12]}",
                session_id=session_id,
                strategy_version_id=strategy_version_id,
                symbol=snapshot.symbol,
                timeframe=timeframe,
                action=action,
                signal_price=decision.signal_price if decision.signal_price is not None else snapshot.latest_price,
                confidence=decision.confidence,
                reason_codes=[error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED],
                snapshot_time=snapshot.snapshot_time,
                blocked=True,
                explain_payload=self.build_hybrid_explain_payload(
                    strategy_config=strategy_config,
                    snapshot=snapshot,
                    fallback_decision="SIGNAL_DEDUPED",
                    risk_blocks=[error_codes.EXEC_DUPLICATE_SIGNAL_IGNORED],
                ),
            )

        self._signal_dedupe[dedupe_key] = datetime.now(UTC)
        logger.info("Hybrid signal generated", extra={"session_id": session_id, "symbol": snapshot.symbol, "reason_codes": decision.reason_codes})
        return Signal(
            id=f"sig_{uuid4().hex[:12]}",
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            signal_price=decision.signal_price if decision.signal_price is not None else snapshot.latest_price,
            confidence=decision.confidence,
            reason_codes=decision.reason_codes or ["HYBRID_ENTRY_CONDITION_MET"],
            snapshot_time=snapshot.snapshot_time,
            blocked=False,
            explain_payload=explain_payload,
        )

    def _plugin_config(self, strategy_config: dict[str, object]) -> dict[str, object]:
        plugin_config = strategy_config.get("plugin_config")
        return plugin_config if isinstance(plugin_config, dict) else {}
