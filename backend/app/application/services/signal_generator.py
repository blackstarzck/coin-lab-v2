from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from ...core import error_codes
from ...core.logging import get_logger
from ...domain.entities.market import MarketSnapshot
from ...domain.entities.session import Signal, SignalAction
from .strategy_runtime_evaluator import EvaluationResult, StrategyRuntimeEvaluator

logger = get_logger(__name__)


class SignalGenerator:
    def __init__(self, runtime_evaluator: StrategyRuntimeEvaluator | None = None) -> None:
        self.runtime_evaluator = runtime_evaluator or StrategyRuntimeEvaluator()
        self._signal_dedupe: dict[str, datetime] = {}

    def evaluate(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        session_id: str,
        strategy_version_id: str,
    ) -> Signal | None:
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
