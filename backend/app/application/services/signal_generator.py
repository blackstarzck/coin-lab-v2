from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from ...core import error_codes
from ...core.logging import get_logger
from ...domain.entities.market import MarketSnapshot
from ...domain.entities.session import Signal, SignalAction

logger = get_logger(__name__)


class SignalGenerator:
    def __init__(self) -> None:
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

        matched, reasons = self._evaluate_condition_tree(entry_node, snapshot)
        if not matched:
            logger.debug("Signal conditions not met", extra={"session_id": session_id, "symbol": snapshot.symbol})
            return None

        market = self._as_dict(strategy_config.get("market"))
        tf_raw = market.get("timeframes")
        timeframes = tf_raw if isinstance(tf_raw, list) else []
        timeframe = str(timeframes[0]) if timeframes else "1m"
        action = SignalAction.ENTER.value
        snapshot_key = f"{snapshot.symbol}|{timeframe}|{snapshot.snapshot_time.isoformat()}"
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
            )

        self._signal_dedupe[dedupe_key] = datetime.now(UTC)
        logger.info("Signal generated", extra={"session_id": session_id, "symbol": snapshot.symbol, "reason_codes": reasons})
        return Signal(
            id=f"sig_{uuid4().hex[:12]}",
            session_id=session_id,
            strategy_version_id=strategy_version_id,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            action=action,
            signal_price=snapshot.latest_price,
            confidence=1.0,
            reason_codes=reasons or ["ENTRY_CONDITION_MET"],
            snapshot_time=snapshot.snapshot_time,
            blocked=False,
        )

    def _evaluate_condition_tree(self, node: dict[str, object], snapshot: MarketSnapshot) -> tuple[bool, list[str]]:
        logic = str(node.get("logic", "all")).lower()
        conditions = node.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            return True, ["ENTRY_EMPTY_CONDITIONS_MVP_TRUE"]

        condition_nodes = [self._as_dict(item) for item in conditions if isinstance(item, dict)]

        if logic == "all":
            reasons: list[str] = []
            for child in condition_nodes:
                result, child_reasons = self._evaluate_node(child, snapshot)
                reasons.extend(child_reasons)
                if not result:
                    return False, reasons
            return True, reasons

        if logic == "any":
            reasons: list[str] = []
            any_true = False
            for child in condition_nodes:
                result, child_reasons = self._evaluate_node(child, snapshot)
                reasons.extend(child_reasons)
                any_true = any_true or result
            return any_true, reasons

        if logic == "not":
            child = condition_nodes[0] if condition_nodes else {}
            result, reasons = self._evaluate_node(child, snapshot)
            return (not result), reasons

        return False, ["ENTRY_UNKNOWN_LOGIC"]

    def _evaluate_leaf(self, leaf: dict[str, object], snapshot: MarketSnapshot) -> tuple[bool, list[str]]:
        op = str(leaf.get("operator", "")).lower()
        latest = snapshot.latest_price
        if latest is None:
            return False, ["ENTRY_NO_LATEST_PRICE"]

        target = leaf.get("value")
        target_value = self._as_float_optional(target)

        if op in {"price_gt", "gt"} and target_value is not None:
            return latest > target_value, ["LEAF_PRICE_GT"]
        if op in {"price_gte", "gte"} and target_value is not None:
            return latest >= target_value, ["LEAF_PRICE_GTE"]
        if op in {"price_lt", "lt"} and target_value is not None:
            return latest < target_value, ["LEAF_PRICE_LT"]
        if op in {"price_lte", "lte"} and target_value is not None:
            return latest <= target_value, ["LEAF_PRICE_LTE"]

        timeframe = str(leaf.get("timeframe", "1m"))
        candle = snapshot.candles.get(timeframe)
        if candle is not None and target_value is not None:
            if op == "close_gt":
                return candle.close > target_value, ["LEAF_CLOSE_GT"]
            if op == "high_breakout":
                return candle.high > target_value, ["LEAF_HIGH_BREAKOUT"]

        return True, [f"MVP_STUB_{op or 'unknown'}"]

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

    def _evaluate_node(self, node: dict[str, object], snapshot: MarketSnapshot) -> tuple[bool, list[str]]:
        if "conditions" in node and "logic" in node:
            return self._evaluate_condition_tree(node, snapshot)
        return self._evaluate_leaf(node, snapshot)

    def _as_dict(self, value: object) -> dict[str, object]:
        return cast(dict[str, object], value) if isinstance(value, dict) else {}

    def _as_float_optional(self, value: object) -> float | None:
        return float(value) if isinstance(value, int | float) else None
