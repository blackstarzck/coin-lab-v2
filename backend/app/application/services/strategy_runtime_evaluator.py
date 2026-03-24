from __future__ import annotations

from dataclasses import dataclass
from math import isclose, sqrt
from typing import cast

from ...domain.entities.market import CandleState, MarketSnapshot

ExplainScalar = float | int | bool | str | None
ExplainItem = dict[str, ExplainScalar]


@dataclass(slots=True)
class EvaluationResult:
    matched: bool
    reason_codes: list[str]
    matched_conditions: list[str]
    failed_conditions: list[str]
    facts: list[ExplainItem]
    parameters: list[ExplainItem]


@dataclass(slots=True)
class SourceResolution:
    ready: bool
    value: float | None
    label: str
    facts: list[ExplainItem]
    parameters: list[ExplainItem]
    reason_code: str | None = None


class StrategyRuntimeEvaluator:
    def evaluate(
        self,
        node: dict[str, object],
        snapshot: MarketSnapshot,
        *,
        path: str,
        default_timeframe: str,
    ) -> EvaluationResult:
        if "logic" in node:
            return self._evaluate_logic_block(node, snapshot, path=path, default_timeframe=default_timeframe)
        return self._evaluate_leaf(node, snapshot, path=path, default_timeframe=default_timeframe)

    def build_explain_payload(
        self,
        *,
        snapshot_key: str,
        decision: str,
        result: EvaluationResult,
        risk_blocks: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "snapshot_key": snapshot_key,
            "decision": decision,
            "reason_codes": self._dedupe_strings(result.reason_codes),
            "facts": self._dedupe_items([*result.facts, *result.parameters]),
            "parameters": self._dedupe_items(result.parameters),
            "matched_conditions": self._dedupe_strings(result.matched_conditions),
            "failed_conditions": self._dedupe_strings(result.failed_conditions),
            "risk_blocks": self._dedupe_strings(risk_blocks or []),
        }

    def _evaluate_logic_block(
        self,
        node: dict[str, object],
        snapshot: MarketSnapshot,
        *,
        path: str,
        default_timeframe: str,
    ) -> EvaluationResult:
        logic = str(node.get("logic", "all")).lower()
        if logic in {"all", "any"}:
            raw_conditions = node.get("conditions")
            conditions = cast(list[object], raw_conditions) if isinstance(raw_conditions, list) else []
            if not conditions:
                return EvaluationResult(
                    matched=False,
                    reason_codes=["DSL_EMPTY_CONDITIONS"],
                    matched_conditions=[],
                    failed_conditions=[path],
                    facts=[],
                    parameters=[],
                )
            results: list[EvaluationResult] = []
            for index, child in enumerate(conditions):
                if not isinstance(child, dict):
                    results.append(
                        EvaluationResult(
                            matched=False,
                            reason_codes=["DSL_INVALID_CONDITION_NODE"],
                            matched_conditions=[],
                            failed_conditions=[f"{path}.conditions[{index}]"],
                            facts=[],
                            parameters=[],
                        )
                    )
                    continue
                results.append(
                    self.evaluate(
                        self._as_dict(child),
                        snapshot,
                        path=f"{path}.conditions[{index}]",
                        default_timeframe=default_timeframe,
                    )
                )
            matched = all(item.matched for item in results) if logic == "all" else any(item.matched for item in results)
            matched_conditions: list[str] = []
            failed_conditions: list[str] = []
            reason_codes: list[str] = []
            facts: list[ExplainItem] = []
            parameters: list[ExplainItem] = []
            for item in results:
                matched_conditions.extend(item.matched_conditions)
                failed_conditions.extend(item.failed_conditions)
                reason_codes.extend(item.reason_codes)
                facts.extend(item.facts)
                parameters.extend(item.parameters)
            return EvaluationResult(
                matched=matched,
                reason_codes=self._dedupe_strings(reason_codes),
                matched_conditions=self._dedupe_strings(matched_conditions),
                failed_conditions=self._dedupe_strings(failed_conditions),
                facts=self._dedupe_items(facts),
                parameters=self._dedupe_items(parameters),
            )

        if logic == "not":
            child = cast(dict[str, object], node.get("condition")) if isinstance(node.get("condition"), dict) else {}
            result = self.evaluate(child, snapshot, path=f"{path}.condition", default_timeframe=default_timeframe)
            return EvaluationResult(
                matched=not result.matched,
                reason_codes=result.reason_codes or ["DSL_NOT_EVALUATED"],
                matched_conditions=[path] if not result.matched else [],
                failed_conditions=[] if not result.matched else [path],
                facts=result.facts,
                parameters=result.parameters,
            )

        return EvaluationResult(
            matched=False,
            reason_codes=["DSL_UNKNOWN_LOGIC"],
            matched_conditions=[],
            failed_conditions=[path],
            facts=[],
            parameters=[],
        )

    def _evaluate_leaf(
        self,
        leaf: dict[str, object],
        snapshot: MarketSnapshot,
        *,
        path: str,
        default_timeframe: str,
    ) -> EvaluationResult:
        leaf_type = str(leaf.get("type", "")).lower()
        if not leaf_type:
            return self._evaluate_legacy_leaf(leaf, snapshot, path=path, default_timeframe=default_timeframe)

        if leaf_type in {"indicator_compare", "threshold_compare"}:
            left = self._resolve_source(self._as_dict(leaf.get("left")), snapshot, default_timeframe, f"{path}.left")
            right = self._resolve_source(self._as_dict(leaf.get("right")), snapshot, default_timeframe, f"{path}.right")
            operator = str(leaf.get("operator", ""))
            return self._compare_resolutions(
                leaf_type=leaf_type,
                operator=operator,
                left=left,
                right=right,
                path=path,
            )

        if leaf_type in {"cross_over", "cross_under"}:
            lookback_bars = self._as_int(leaf.get("lookback_bars"), 1)
            left_prev = self._resolve_source(self._as_dict(leaf.get("left")), snapshot, default_timeframe, f"{path}.left", offset=lookback_bars)
            right_prev = self._resolve_source(self._as_dict(leaf.get("right")), snapshot, default_timeframe, f"{path}.right", offset=lookback_bars)
            left_now = self._resolve_source(self._as_dict(leaf.get("left")), snapshot, default_timeframe, f"{path}.left")
            right_now = self._resolve_source(self._as_dict(leaf.get("right")), snapshot, default_timeframe, f"{path}.right")
            facts = [*left_prev.facts, *right_prev.facts, *left_now.facts, *right_now.facts]
            parameters = [
                *left_prev.parameters,
                *right_prev.parameters,
                *left_now.parameters,
                *right_now.parameters,
                self._item(f"{path}.lookback_bars", lookback_bars),
            ]
            if not all(item.ready and item.value is not None for item in (left_prev, right_prev, left_now, right_now)):
                not_ready_codes = [item.reason_code for item in (left_prev, right_prev, left_now, right_now) if item.reason_code]
                return self._leaf_result(
                    matched=False,
                    path=path,
                    reason_codes=not_ready_codes or ["SOURCE_NOT_READY"],
                    facts=facts,
                    parameters=parameters,
                )
            if leaf_type == "cross_over":
                matched = cast(float, left_prev.value) <= cast(float, right_prev.value) and cast(float, left_now.value) > cast(float, right_now.value)
            else:
                matched = cast(float, left_prev.value) >= cast(float, right_prev.value) and cast(float, left_now.value) < cast(float, right_now.value)
            return self._leaf_result(
                matched=matched,
                path=path,
                reason_codes=[self._reason_code_for_leaf(leaf_type, leaf)],
                facts=facts,
                parameters=parameters,
            )

        if leaf_type == "price_breakout":
            source = self._resolve_source(self._as_dict(leaf.get("source")), snapshot, default_timeframe, f"{path}.source")
            reference = self._resolve_source(self._as_dict(leaf.get("reference")), snapshot, default_timeframe, f"{path}.reference")
            operator = str(leaf.get("operator", ""))
            return self._compare_resolutions(
                leaf_type=leaf_type,
                operator=operator,
                left=source,
                right=reference,
                path=path,
            )

        if leaf_type == "volume_spike":
            source = self._resolve_source(self._as_dict(leaf.get("source")), snapshot, default_timeframe, f"{path}.source")
            threshold = self._as_float_optional(leaf.get("threshold"))
            facts = [*source.facts]
            parameters = [*source.parameters]
            if threshold is not None:
                facts.append(self._item(f"{path}.threshold", threshold))
                parameters.append(self._item(f"{path}.threshold", threshold))
            if not source.ready or source.value is None or threshold is None:
                return self._leaf_result(
                    matched=False,
                    path=path,
                    reason_codes=[source.reason_code or "SOURCE_NOT_READY"],
                    facts=facts,
                    parameters=parameters,
                )
            matched = self._compare(cast(float, source.value), str(leaf.get("operator", ">=")), threshold)
            return self._leaf_result(
                matched=matched,
                path=path,
                reason_codes=[self._reason_code_for_leaf(leaf_type, leaf)],
                facts=facts,
                parameters=parameters,
            )

        if leaf_type == "rsi_range":
            source = self._resolve_source(self._as_dict(leaf.get("source")), snapshot, default_timeframe, f"{path}.source")
            min_value = self._as_float_optional(leaf.get("min"))
            max_value = self._as_float_optional(leaf.get("max"))
            facts = [*source.facts]
            parameters = [*source.parameters]
            if min_value is not None:
                facts.append(self._item(f"{path}.min", min_value))
                parameters.append(self._item(f"{path}.min", min_value))
            if max_value is not None:
                facts.append(self._item(f"{path}.max", max_value))
                parameters.append(self._item(f"{path}.max", max_value))
            if not source.ready or source.value is None or min_value is None or max_value is None:
                return self._leaf_result(
                    matched=False,
                    path=path,
                    reason_codes=[source.reason_code or "SOURCE_NOT_READY"],
                    facts=facts,
                    parameters=parameters,
                )
            matched = min_value <= cast(float, source.value) <= max_value
            return self._leaf_result(
                matched=matched,
                path=path,
                reason_codes=[self._reason_code_for_leaf(leaf_type, leaf)],
                facts=facts,
                parameters=parameters,
            )

        if leaf_type == "candle_pattern":
            timeframe = self._timeframe_for_ref(leaf, default_timeframe)
            candles = self._series(snapshot, timeframe)
            pattern = str(leaf.get("pattern", ""))
            matched, facts = self._evaluate_candle_pattern(pattern, candles, path)
            parameters = [
                self._item(f"{path}.pattern", pattern),
                self._item(f"{path}.timeframe", timeframe),
            ]
            return self._leaf_result(
                matched=matched,
                path=path,
                reason_codes=[self._reason_code_for_leaf(leaf_type, leaf)],
                facts=facts,
                parameters=parameters,
            )

        if leaf_type == "regime_match":
            timeframe = self._timeframe_for_ref(leaf, default_timeframe)
            closes = [candle.close for candle in self._series(snapshot, timeframe)]
            regime = str(leaf.get("regime", ""))
            matched, facts = self._evaluate_regime_match(regime, closes, path)
            return self._leaf_result(
                matched=matched,
                path=path,
                reason_codes=[self._reason_code_for_leaf(leaf_type, leaf)],
                facts=facts,
                parameters=[self._item(f"{path}.regime", regime), self._item(f"{path}.timeframe", timeframe)],
            )

        return self._leaf_result(
            matched=False,
            path=path,
            reason_codes=["DSL_UNSUPPORTED_LEAF"],
            facts=[],
            parameters=[],
        )

    def _evaluate_legacy_leaf(
        self,
        leaf: dict[str, object],
        snapshot: MarketSnapshot,
        *,
        path: str,
        default_timeframe: str,
    ) -> EvaluationResult:
        operator = str(leaf.get("operator", "")).lower()
        threshold = self._as_float_optional(leaf.get("value"))
        facts: list[ExplainItem] = []
        parameters: list[ExplainItem] = []
        latest = snapshot.latest_price
        if latest is not None:
            facts.append(self._item("latest_price", latest))
        if threshold is not None:
            facts.append(self._item(f"{path}.value", threshold))
            parameters.append(self._item(f"{path}.value", threshold))
        if latest is None:
            return self._leaf_result(matched=False, path=path, reason_codes=["ENTRY_NO_LATEST_PRICE"], facts=facts, parameters=parameters)
        if operator in {"price_gt", "gt"} and threshold is not None:
            return self._leaf_result(matched=latest > threshold, path=path, reason_codes=["LEAF_PRICE_GT"], facts=facts, parameters=parameters)
        if operator in {"price_gte", "gte"} and threshold is not None:
            return self._leaf_result(matched=latest >= threshold, path=path, reason_codes=["LEAF_PRICE_GTE"], facts=facts, parameters=parameters)
        if operator in {"price_lt", "lt"} and threshold is not None:
            return self._leaf_result(matched=latest < threshold, path=path, reason_codes=["LEAF_PRICE_LT"], facts=facts, parameters=parameters)
        if operator in {"price_lte", "lte"} and threshold is not None:
            return self._leaf_result(matched=latest <= threshold, path=path, reason_codes=["LEAF_PRICE_LTE"], facts=facts, parameters=parameters)

        timeframe = str(leaf.get("timeframe", default_timeframe))
        candle = snapshot.candles.get(timeframe)
        if candle is not None and threshold is not None:
            facts.extend(
                [
                    self._item(f"{timeframe}.close", candle.close),
                    self._item(f"{timeframe}.high", candle.high),
                ]
            )
            if operator == "close_gt":
                return self._leaf_result(matched=candle.close > threshold, path=path, reason_codes=["LEAF_CLOSE_GT"], facts=facts, parameters=parameters)
            if operator == "high_breakout":
                return self._leaf_result(matched=candle.high > threshold, path=path, reason_codes=["LEAF_HIGH_BREAKOUT"], facts=facts, parameters=parameters)

        return self._leaf_result(matched=True, path=path, reason_codes=[f"MVP_STUB_{operator or 'unknown'}"], facts=facts, parameters=parameters)

    def _compare_resolutions(
        self,
        *,
        leaf_type: str,
        operator: str,
        left: SourceResolution,
        right: SourceResolution,
        path: str,
    ) -> EvaluationResult:
        facts = [*left.facts, *right.facts]
        parameters = [*left.parameters, *right.parameters]
        if not left.ready or not right.ready or left.value is None or right.value is None:
            reason_codes = [item for item in (left.reason_code, right.reason_code) if item]
            return self._leaf_result(
                matched=False,
                path=path,
                reason_codes=reason_codes or ["SOURCE_NOT_READY"],
                facts=facts,
                parameters=parameters,
            )
        matched = self._compare(cast(float, left.value), operator, cast(float, right.value))
        return self._leaf_result(
            matched=matched,
            path=path,
            reason_codes=[self._reason_code_for_leaf(leaf_type, {})],
            facts=facts,
            parameters=parameters,
        )

    def _resolve_source(
        self,
        ref: dict[str, object],
        snapshot: MarketSnapshot,
        default_timeframe: str,
        label_prefix: str,
        *,
        offset: int = 0,
    ) -> SourceResolution:
        kind = str(ref.get("kind", "")).lower()
        timeframe = self._timeframe_for_ref(ref, default_timeframe)
        parameters = self._source_parameters(ref, label_prefix, timeframe)
        if kind == "constant":
            value = self._as_float_optional(ref.get("value"))
            facts = [self._item(self._source_label(ref), value)] if value is not None else []
            return SourceResolution(
                ready=value is not None,
                value=value,
                label=self._source_label(ref),
                facts=facts,
                parameters=parameters,
                reason_code=None if value is not None else "CONSTANT_NOT_READY",
            )

        if kind == "price":
            candle = self._candle_at(snapshot, timeframe, offset)
            field = str(ref.get("field", "close")).lower()
            value = self._price_from_candle(snapshot, candle, field)
            facts = [self._item(self._source_label(ref), value)] if value is not None else []
            return SourceResolution(
                ready=value is not None,
                value=value,
                label=self._source_label(ref),
                facts=facts,
                parameters=parameters,
                reason_code=None if value is not None else "PRICE_NOT_READY",
            )

        if kind == "indicator":
            name = str(ref.get("name", "")).lower()
            closes = [candle.close for candle in self._series(snapshot, timeframe)]
            usable = closes[: len(closes) - offset] if offset > 0 else closes
            value = None
            if name == "ema":
                value = self._ema(usable, self._as_int(self._params(ref).get("length"), 0))
            elif name == "rsi":
                value = self._rsi(usable, self._indicator_length(ref, default=14))
            facts = [self._item(self._source_label(ref), value)] if value is not None else []
            return SourceResolution(
                ready=value is not None,
                value=value,
                label=self._source_label(ref),
                facts=facts,
                parameters=parameters,
                reason_code=None if value is not None else f"{name.upper()}_NOT_READY",
            )

        if kind == "derived":
            name = str(ref.get("name", "")).lower()
            candles = self._series(snapshot, timeframe)
            value = None
            if name == "highest_high":
                value = self._highest_high(candles, self._as_int(self._params(ref).get("lookback"), 0), bool(self._params(ref).get("exclude_current", False)), offset)
            elif name == "lowest_low":
                value = self._lowest_low(candles, self._as_int(self._params(ref).get("lookback"), 0), bool(self._params(ref).get("exclude_current", False)), offset)
            elif name == "volume_ratio":
                value = self._volume_ratio(candles, self._as_int(self._params(ref).get("lookback"), 0), offset)
            facts = [self._item(self._source_label(ref), value)] if value is not None else []
            return SourceResolution(
                ready=value is not None,
                value=value,
                label=self._source_label(ref),
                facts=facts,
                parameters=parameters,
                reason_code=None if value is not None else f"{name.upper()}_NOT_READY",
            )

        return SourceResolution(
            ready=False,
            value=None,
            label=self._source_label(ref),
            facts=[],
            parameters=parameters,
            reason_code="INVALID_SOURCE_REF",
        )

    def _series(self, snapshot: MarketSnapshot, timeframe: str) -> list[CandleState]:
        history = list(snapshot.candle_history.get(timeframe, ()))
        current = snapshot.candles.get(timeframe)
        if current is None:
            return history
        if not history:
            return [current]
        if history[-1].candle_start == current.candle_start:
            history[-1] = current
        else:
            history.append(current)
        return history

    def _candle_at(self, snapshot: MarketSnapshot, timeframe: str, offset: int) -> CandleState | None:
        series = self._series(snapshot, timeframe)
        if len(series) <= offset:
            return None
        return series[-1 - offset]

    def _price_from_candle(self, snapshot: MarketSnapshot, candle: CandleState | None, field: str) -> float | None:
        if field == "close":
            if candle is not None:
                return candle.close
            return snapshot.latest_price
        if candle is None:
            return None
        if field == "open":
            return candle.open
        if field == "high":
            return candle.high
        if field == "low":
            return candle.low
        if field == "volume":
            return candle.volume
        return None

    def _highest_high(self, candles: list[CandleState], lookback: int, exclude_current: bool, offset: int) -> float | None:
        window = self._window(candles, lookback, exclude_current, offset)
        if window is None:
            return None
        return max(candle.high for candle in window)

    def _lowest_low(self, candles: list[CandleState], lookback: int, exclude_current: bool, offset: int) -> float | None:
        window = self._window(candles, lookback, exclude_current, offset)
        if window is None:
            return None
        return min(candle.low for candle in window)

    def _window(self, candles: list[CandleState], lookback: int, exclude_current: bool, offset: int) -> list[CandleState] | None:
        if lookback <= 0:
            return None
        end = len(candles) - offset
        if exclude_current:
            end -= 1
        start = end - lookback
        if start < 0 or end <= 0:
            return None
        window = candles[start:end]
        return window if len(window) == lookback else None

    def _volume_ratio(self, candles: list[CandleState], lookback: int, offset: int) -> float | None:
        if lookback <= 0:
            return None
        target_index = len(candles) - 1 - offset
        history_end = target_index
        history_start = history_end - lookback
        if history_start < 0 or target_index < 0:
            return None
        baseline = candles[history_start:history_end]
        if len(baseline) != lookback:
            return None
        average_volume = sum(candle.volume for candle in baseline) / lookback
        if average_volume <= 0:
            return None
        return candles[target_index].volume / average_volume

    def _ema(self, values: list[float], length: int) -> float | None:
        if length <= 0 or len(values) < length:
            return None
        multiplier = 2 / (length + 1)
        ema = sum(values[:length]) / length
        for value in values[length:]:
            ema = (value - ema) * multiplier + ema
        return ema

    def _rsi(self, values: list[float], length: int) -> float | None:
        if length <= 0 or len(values) < length + 1:
            return None
        gains = 0.0
        losses = 0.0
        for index in range(1, length + 1):
            delta = values[index] - values[index - 1]
            if delta >= 0:
                gains += delta
            else:
                losses -= delta
        avg_gain = gains / length
        avg_loss = losses / length
        for index in range(length + 1, len(values)):
            delta = values[index] - values[index - 1]
            gain = max(delta, 0.0)
            loss = max(-delta, 0.0)
            avg_gain = ((avg_gain * (length - 1)) + gain) / length
            avg_loss = ((avg_loss * (length - 1)) + loss) / length
        if isclose(avg_loss, 0.0):
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _evaluate_candle_pattern(self, pattern: str, candles: list[CandleState], path: str) -> tuple[bool, list[ExplainItem]]:
        facts: list[ExplainItem] = []
        if len(candles) < 2:
            return False, facts
        current = candles[-1]
        previous = candles[-2]
        facts.extend(
            [
                self._item(f"{path}.current.open", current.open),
                self._item(f"{path}.current.close", current.close),
                self._item(f"{path}.current.high", current.high),
                self._item(f"{path}.current.low", current.low),
                self._item(f"{path}.previous.open", previous.open),
                self._item(f"{path}.previous.close", previous.close),
            ]
        )
        if pattern == "bullish_engulfing":
            return previous.close < previous.open and current.close > current.open and current.open <= previous.close and current.close >= previous.open, facts
        if pattern == "bearish_engulfing":
            return previous.close > previous.open and current.close < current.open and current.open >= previous.close and current.close <= previous.open, facts
        if pattern == "inside_bar_break":
            if len(candles) < 3:
                return False, facts
            base = candles[-3]
            facts.extend(
                [
                    self._item(f"{path}.base.high", base.high),
                    self._item(f"{path}.base.low", base.low),
                ]
            )
            inside = previous.high <= base.high and previous.low >= base.low
            breakout = current.close > previous.high or current.close < previous.low
            return inside and breakout, facts
        if pattern == "long_lower_wick":
            body = abs(current.close - current.open)
            lower_wick = min(current.close, current.open) - current.low
            upper_wick = current.high - max(current.close, current.open)
            facts.extend(
                [
                    self._item(f"{path}.body", body),
                    self._item(f"{path}.lower_wick", lower_wick),
                    self._item(f"{path}.upper_wick", upper_wick),
                ]
            )
            return lower_wick > body * 2 and lower_wick > upper_wick, facts
        return False, facts

    def _evaluate_regime_match(self, regime: str, closes: list[float], path: str) -> tuple[bool, list[ExplainItem]]:
        facts: list[ExplainItem] = []
        if len(closes) < 20:
            return False, facts
        ema20 = self._ema(closes, 20)
        ema50 = self._ema(closes, 50)
        latest = closes[-1]
        volatility_ratio = self._volatility_ratio(closes[-20:])
        if ema20 is not None:
            facts.append(self._item(f"{path}.ema20", ema20))
        if ema50 is not None:
            facts.append(self._item(f"{path}.ema50", ema50))
        facts.append(self._item(f"{path}.close", latest))
        if volatility_ratio is not None:
            facts.append(self._item(f"{path}.volatility_ratio", volatility_ratio))

        if regime == "trend_up":
            return bool(ema20 is not None and ema50 is not None and ema20 > ema50 and latest >= ema20), facts
        if regime == "trend_down":
            return bool(ema20 is not None and ema50 is not None and ema20 < ema50 and latest <= ema20), facts
        if regime == "range":
            if ema20 is None or ema50 is None or latest <= 0:
                return False, facts
            return abs(ema20 - ema50) / latest <= 0.0025, facts
        if regime == "high_volatility":
            return bool(volatility_ratio is not None and volatility_ratio >= 0.02), facts
        if regime == "low_volatility":
            return bool(volatility_ratio is not None and volatility_ratio <= 0.01), facts
        return False, facts

    def _volatility_ratio(self, values: list[float]) -> float | None:
        if len(values) < 2:
            return None
        mean = sum(values) / len(values)
        if mean == 0:
            return None
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return sqrt(variance) / mean

    def _compare(self, left: float, operator: str, right: float) -> bool:
        if operator == ">":
            return left > right
        if operator == ">=":
            return left >= right
        if operator == "<":
            return left < right
        if operator == "<=":
            return left <= right
        if operator == "==":
            return isclose(left, right)
        if operator == "!=":
            return not isclose(left, right)
        return False

    def _leaf_result(
        self,
        *,
        matched: bool,
        path: str,
        reason_codes: list[str],
        facts: list[ExplainItem],
        parameters: list[ExplainItem],
    ) -> EvaluationResult:
        return EvaluationResult(
            matched=matched,
            reason_codes=self._dedupe_strings(reason_codes),
            matched_conditions=[path] if matched else [],
            failed_conditions=[] if matched else [path],
            facts=self._dedupe_items(facts),
            parameters=self._dedupe_items(parameters),
        )

    def _source_label(self, ref: dict[str, object]) -> str:
        kind = str(ref.get("kind", "")).lower()
        if kind == "indicator":
            name = str(ref.get("name", "indicator")).lower()
            length = self._params(ref).get("length")
            if isinstance(length, int | float):
                return f"{name}{int(length)}"
            return name
        if kind == "derived":
            name = str(ref.get("name", "derived")).lower()
            lookback = self._params(ref).get("lookback")
            if isinstance(lookback, int | float):
                return f"{name}{int(lookback)}"
            return name
        if kind == "price":
            return str(ref.get("field", "price")).lower()
        if kind == "constant":
            return "constant"
        return "value"

    def _source_parameters(self, ref: dict[str, object], label_prefix: str, timeframe: str) -> list[ExplainItem]:
        items: list[ExplainItem] = [self._item(f"{label_prefix}.timeframe", timeframe)]
        kind = str(ref.get("kind", "")).lower()
        if kind:
            items.append(self._item(f"{label_prefix}.kind", kind))
        if kind == "price" and isinstance(ref.get("field"), str):
            items.append(self._item(f"{label_prefix}.field", str(ref["field"])))
        if kind in {"indicator", "derived"} and isinstance(ref.get("name"), str):
            items.append(self._item(f"{label_prefix}.name", str(ref["name"])))
        if kind == "constant":
            items.append(self._item(f"{label_prefix}.value", ref.get("value")))
        for param_name, param_value in self._params(ref).items():
            items.append(self._item(f"{label_prefix}.params.{param_name}", param_value))
        return items

    def _params(self, ref: dict[str, object]) -> dict[str, object]:
        value = ref.get("params")
        return cast(dict[str, object], value) if isinstance(value, dict) else {}

    def _indicator_length(self, ref: dict[str, object], *, default: int) -> int:
        raw = self._params(ref).get("length")
        if isinstance(raw, int) and raw > 0:
            return raw
        return default

    def _timeframe_for_ref(self, ref: dict[str, object], default_timeframe: str) -> str:
        for key in ("timeframe", "base"):
            value = ref.get(key)
            if isinstance(value, str) and value:
                return value
        return default_timeframe

    def _reason_code_for_leaf(self, leaf_type: str, leaf: dict[str, object]) -> str:
        if leaf_type == "indicator_compare":
            return "INDICATOR_COMPARE_MATCH"
        if leaf_type == "threshold_compare":
            return "THRESHOLD_COMPARE_MATCH"
        if leaf_type == "cross_over":
            return "CROSS_OVER_MATCH"
        if leaf_type == "cross_under":
            return "CROSS_UNDER_MATCH"
        if leaf_type == "price_breakout":
            reference = cast(dict[str, object], leaf.get("reference")) if isinstance(leaf.get("reference"), dict) else {}
            lookback = self._params(reference).get("lookback")
            if isinstance(lookback, int | float):
                return f"PRICE_BREAKOUT_{int(lookback)}"
            return "PRICE_BREAKOUT_MATCH"
        if leaf_type == "volume_spike":
            return "VOLUME_SPIKE_MATCH"
        if leaf_type == "rsi_range":
            return "RSI_RANGE_MATCH"
        if leaf_type == "candle_pattern":
            pattern = str(leaf.get("pattern", "pattern")).upper()
            return f"{pattern}_MATCH"
        if leaf_type == "regime_match":
            regime = str(leaf.get("regime", "regime")).upper()
            return f"REGIME_{regime}"
        return f"{leaf_type.upper()}_MATCH"

    def _item(self, label: str, value: ExplainScalar) -> ExplainItem:
        return {
            "label": label,
            "value": value,
        }

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if not value or value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _dedupe_items(self, values: list[ExplainItem]) -> list[ExplainItem]:
        seen: set[tuple[str, str]] = set()
        ordered: list[ExplainItem] = []
        for item in values:
            label = str(item.get("label", ""))
            value = item.get("value")
            key = (label, repr(value))
            if not label or key in seen:
                continue
            seen.add(key)
            ordered.append({"label": label, "value": value})
        return ordered

    def _as_int(self, value: object, fallback: int) -> int:
        return int(value) if isinstance(value, int | float) else fallback

    def _as_float_optional(self, value: object) -> float | None:
        return float(value) if isinstance(value, int | float) else None

    def _as_dict(self, value: object) -> dict[str, object]:
        return cast(dict[str, object], value) if isinstance(value, dict) else {}
