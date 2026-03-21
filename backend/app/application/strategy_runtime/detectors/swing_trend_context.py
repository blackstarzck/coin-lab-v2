from __future__ import annotations

from app.domain.strategy_runtime import DetectorResult, ExplainItem, TrendContext

from .base import (
    DetectorContext,
    StructureDetector,
    build_structure_id,
    history_not_ready_result,
    resolve_candles,
    timeframe_missing_result,
)


def _direction_to_state(direction: str) -> str:
    if direction == "bullish":
        return "trend_up"
    if direction == "bearish":
        return "trend_down"
    raise ValueError(f"unsupported direction: {direction}")


class SwingTrendContextDetector(StructureDetector[TrendContext]):
    detector_id = "swing_trend_context"

    def required_history(self, config: dict[str, object]) -> int:
        width = int(config.get("width", 3))
        return max((width * 2) + 4, 6)

    def evaluate(self, context: DetectorContext) -> DetectorResult[TrendContext]:
        direction = str(context.config.get("direction", "bullish")).strip().lower()
        width = int(context.config.get("width", 3))
        parameters = (
            ExplainItem(label="detector.swing_trend_context.direction", value=direction),
            ExplainItem(label="detector.swing_trend_context.width", value=width),
        )
        candles = resolve_candles(context.snapshot, context.timeframe)
        if not candles:
            return timeframe_missing_result(self.detector_id, parameters=parameters)
        if len(candles) < self.required_history(context.config):
            return history_not_ready_result(
                self.detector_id,
                facts=(ExplainItem(label="detector.swing_trend_context.history_size", value=len(candles)),),
                parameters=parameters,
            )

        swing_lows, swing_highs = self._find_swings(candles, width)
        current_index = len(candles) - 1
        prior_lows = [index for index in swing_lows if index < current_index]
        prior_highs = [index for index in swing_highs if index < current_index]

        trend_state = "range"
        trend_direction: str | None = None
        support: float | None = None
        resistance: float | None = None
        formed_at = candles[0].candle_start
        confidence = 0.0

        if len(prior_lows) >= 2 and len(prior_highs) >= 2:
            previous_low = candles[prior_lows[-2]]
            latest_low = candles[prior_lows[-1]]
            previous_high = candles[prior_highs[-2]]
            latest_high = candles[prior_highs[-1]]
            support = latest_low.low
            resistance = latest_high.high
            formed_at = min(latest_low.candle_start, latest_high.candle_start)
            higher_low = latest_low.low > previous_low.low
            lower_low = latest_low.low < previous_low.low
            higher_high = latest_high.high > previous_high.high
            lower_high = latest_high.high < previous_high.high

            if higher_low and higher_high:
                trend_state = "trend_up"
                trend_direction = "bullish"
                confidence = self._confidence(previous_low.low, latest_low.low, previous_high.high, latest_high.high)
            elif lower_low and lower_high:
                trend_state = "trend_down"
                trend_direction = "bearish"
                confidence = self._confidence(latest_low.low, previous_low.low, latest_high.high, previous_high.high)

        average_close = sum(candle.close for candle in candles[-self.required_history(context.config) :]) / min(
            len(candles),
            self.required_history(context.config),
        )
        facts = (
            ExplainItem(label="detector.swing_trend_context.swing_low_count", value=len(prior_lows)),
            ExplainItem(label="detector.swing_trend_context.swing_high_count", value=len(prior_highs)),
            ExplainItem(label="detector.swing_trend_context.support", value=support),
            ExplainItem(label="detector.swing_trend_context.resistance", value=resistance),
            ExplainItem(label="detector.swing_trend_context.average_close", value=average_close),
            ExplainItem(label="detector.swing_trend_context.trend_state", value=trend_state),
        )
        matched = trend_state == _direction_to_state(direction)
        reason_codes = ("DETECTOR_MATCHED",) if matched else ("DETECTOR_NO_MATCH",)
        trend = TrendContext(
            structure_id=build_structure_id(
                self.detector_id,
                symbol=context.symbol,
                timeframe=context.timeframe,
                formed_at=formed_at,
                direction=trend_direction,
            ),
            kind="trend_context",
            symbol=context.symbol,
            timeframe=context.timeframe,
            direction=trend_direction,
            formed_at=formed_at,
            invalidated_at=None,
            confidence=confidence,
            support=support,
            resistance=resistance,
            average_close=average_close,
            start_close=candles[0].close,
            latest_close=candles[-1].close,
            trend_state=trend_state,
            facts=facts,
            reason_codes=reason_codes,
        )
        return DetectorResult(
            detector_id=self.detector_id,
            ready=True,
            matched=matched,
            items=(trend,),
            primary=trend,
            reason_codes=reason_codes,
            facts=facts,
            parameters=parameters,
        )

    def _find_swings(self, candles: list[object], width: int) -> tuple[list[int], list[int]]:
        lows: list[int] = []
        highs: list[int] = []
        for index in range(width, len(candles) - width):
            current = candles[index]
            if all(current.low < candles[index + offset].low for offset in range(-width, width + 1) if offset != 0):
                lows.append(index)
            if all(current.high > candles[index + offset].high for offset in range(-width, width + 1) if offset != 0):
                highs.append(index)
        return lows, highs

    def _confidence(self, low_a: float, low_b: float, high_a: float, high_b: float) -> float:
        low_delta = max(low_b - low_a, 0.0) / max(abs(low_a), 1e-9)
        high_delta = max(high_b - high_a, 0.0) / max(abs(high_a), 1e-9)
        return min(1.0, (low_delta + high_delta) * 10.0)
