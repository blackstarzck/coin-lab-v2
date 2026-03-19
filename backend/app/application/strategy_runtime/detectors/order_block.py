from __future__ import annotations

from app.domain.strategy_runtime import DetectorResult, ExplainItem, OrderBlockZone

from .base import (
    DetectorContext,
    StructureDetector,
    build_structure_id,
    history_not_ready_result,
    resolve_candles,
    timeframe_missing_result,
)
from .shared import is_strong_directional_candle, zone_retested


class OrderBlockDetector(StructureDetector[OrderBlockZone]):
    detector_id = "order_block"

    def required_history(self, config: dict[str, object]) -> int:
        lookback = int(config.get("lookback", 8))
        return max(lookback + 3, 5)

    def evaluate(self, context: DetectorContext) -> DetectorResult[OrderBlockZone]:
        direction = str(context.config.get("direction", "bullish")).strip().lower()
        lookback = int(context.config.get("lookback", 8))
        body_ratio_threshold = float(context.config.get("body_ratio_threshold", 0.55))
        body_pct_threshold = float(context.config.get("body_pct_threshold", 0.003))
        retest_tolerance_pct = float(context.config.get("retest_tolerance_pct", 0.0015))
        invalidation_buffer_pct = float(context.config.get("invalidation_buffer_pct", 0.002))
        parameters = (
            ExplainItem(label="detector.order_block.direction", value=direction),
            ExplainItem(label="detector.order_block.lookback", value=lookback),
            ExplainItem(label="detector.order_block.body_ratio_threshold", value=body_ratio_threshold),
            ExplainItem(label="detector.order_block.body_pct_threshold", value=body_pct_threshold),
            ExplainItem(label="detector.order_block.retest_tolerance_pct", value=retest_tolerance_pct),
            ExplainItem(label="detector.order_block.invalidation_buffer_pct", value=invalidation_buffer_pct),
        )
        candles = resolve_candles(context.snapshot, context.timeframe)
        if not candles:
            return timeframe_missing_result(self.detector_id, parameters=parameters)
        if len(candles) < self.required_history(context.config):
            return history_not_ready_result(
                self.detector_id,
                facts=(ExplainItem(label="detector.order_block.history_size", value=len(candles)),),
                parameters=parameters,
            )

        current = candles[-1]
        start_index = max(0, len(candles) - 1 - lookback - 3)
        for index in range(len(candles) - 4, start_index - 1, -1):
            candidate = candles[index]
            if direction == "bullish" and candidate.close >= candidate.open:
                continue
            if direction == "bearish" and candidate.close <= candidate.open:
                continue

            impulse = candles[index + 1]
            follow = candles[index + 2]
            matched_impulse, body_ratio, displacement_pct = is_strong_directional_candle(
                impulse,
                direction=direction,
                body_ratio_threshold=body_ratio_threshold,
                body_pct_threshold=body_pct_threshold,
            )
            if not matched_impulse:
                continue

            prior_window = candles[max(0, index - 3):index + 1]
            if direction == "bullish":
                prior_reference = max(candle.high for candle in prior_window)
                structure_break = (
                    max(impulse.close, impulse.high, follow.close, follow.high) > prior_reference
                    and impulse.close > candidate.high
                )
                lower = candidate.low
                upper = candidate.open
                invalidated = any(next_candle.close < lower for next_candle in candles[index + 2:-1])
                invalidation_price = lower * (1.0 - invalidation_buffer_pct)
                active = current.close >= invalidation_price
            else:
                prior_reference = min(candle.low for candle in prior_window)
                structure_break = (
                    min(impulse.close, impulse.low, follow.close, follow.low) < prior_reference
                    and impulse.close < candidate.low
                )
                lower = candidate.open
                upper = candidate.high
                invalidated = any(next_candle.close > upper for next_candle in candles[index + 2:-1])
                invalidation_price = upper * (1.0 + invalidation_buffer_pct)
                active = current.close <= invalidation_price

            if not structure_break or invalidated:
                continue

            retested = zone_retested(
                current,
                lower=lower,
                upper=upper,
                tolerance_pct=retest_tolerance_pct,
                direction=direction,
            )
            facts = (
                ExplainItem(label="detector.order_block.lower", value=lower),
                ExplainItem(label="detector.order_block.upper", value=upper),
                ExplainItem(label="detector.order_block.invalidation_price", value=invalidation_price),
                ExplainItem(label="detector.order_block.retested", value=retested),
                ExplainItem(label="detector.order_block.displacement_pct", value=displacement_pct),
                ExplainItem(label="detector.order_block.body_ratio", value=body_ratio),
            )
            zone = OrderBlockZone(
                structure_id=build_structure_id(
                    self.detector_id,
                    symbol=context.symbol,
                    timeframe=context.timeframe,
                    formed_at=candidate.candle_start,
                    direction=direction,
                ),
                kind="order_block",
                symbol=context.symbol,
                timeframe=context.timeframe,
                direction=direction,
                formed_at=candidate.candle_start,
                invalidated_at=None,
                confidence=min(1.0, displacement_pct / max(body_pct_threshold, 1e-9)),
                lower=lower,
                upper=upper,
                midpoint=(lower + upper) / 2.0,
                invalidation_price=invalidation_price,
                retested=retested,
                active=active,
                source_candle_at=candidate.candle_start,
                impulse_candle_at=impulse.candle_start,
                body_ratio=body_ratio,
                displacement_pct=displacement_pct,
                facts=facts,
                reason_codes=("DETECTOR_MATCHED",),
            )
            return DetectorResult(
                detector_id=self.detector_id,
                ready=True,
                matched=True,
                items=(zone,),
                primary=zone,
                reason_codes=("DETECTOR_MATCHED",),
                facts=facts,
                parameters=parameters,
            )

        return DetectorResult(
            detector_id=self.detector_id,
            ready=True,
            matched=False,
            reason_codes=("DETECTOR_NO_MATCH",),
            parameters=parameters,
        )
