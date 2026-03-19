from __future__ import annotations

from app.domain.strategy_runtime import DetectorResult, ExplainItem, FairValueGapZone

from .base import (
    DetectorContext,
    StructureDetector,
    build_structure_id,
    history_not_ready_result,
    resolve_candles,
    timeframe_missing_result,
)
from .shared import is_strong_directional_candle, zone_retested


class FairValueGapDetector(StructureDetector[FairValueGapZone]):
    detector_id = "fair_value_gap"

    def required_history(self, config: dict[str, object]) -> int:
        return 4

    def evaluate(self, context: DetectorContext) -> DetectorResult[FairValueGapZone]:
        direction = str(context.config.get("direction", "bullish")).strip().lower()
        gap_threshold_pct = float(context.config.get("gap_threshold_pct", 0.001))
        body_ratio_threshold = float(context.config.get("body_ratio_threshold", 0.55))
        body_pct_threshold = float(context.config.get("body_pct_threshold", 0.003))
        retest_tolerance_pct = float(context.config.get("retest_tolerance_pct", 0.0015))
        invalidation_buffer_pct = float(context.config.get("invalidation_buffer_pct", 0.002))
        parameters = (
            ExplainItem(label="detector.fvg.direction", value=direction),
            ExplainItem(label="detector.fvg.gap_threshold_pct", value=gap_threshold_pct),
            ExplainItem(label="detector.fvg.body_ratio_threshold", value=body_ratio_threshold),
            ExplainItem(label="detector.fvg.body_pct_threshold", value=body_pct_threshold),
            ExplainItem(label="detector.fvg.retest_tolerance_pct", value=retest_tolerance_pct),
            ExplainItem(label="detector.fvg.invalidation_buffer_pct", value=invalidation_buffer_pct),
        )
        candles = resolve_candles(context.snapshot, context.timeframe)
        if not candles:
            return timeframe_missing_result(self.detector_id, parameters=parameters)
        if len(candles) < self.required_history(context.config):
            return history_not_ready_result(
                self.detector_id,
                facts=(ExplainItem(label="detector.fvg.history_size", value=len(candles)),),
                parameters=parameters,
            )

        current = candles[-1]
        for index in range(len(candles) - 4, -1, -1):
            left = candles[index]
            middle = candles[index + 1]
            right = candles[index + 2]
            matched_impulse, body_ratio, body_pct = is_strong_directional_candle(
                middle,
                direction=direction,
                body_ratio_threshold=body_ratio_threshold,
                body_pct_threshold=body_pct_threshold,
            )
            if not matched_impulse:
                continue

            if direction == "bullish":
                if right.low <= left.high:
                    continue
                lower = left.high
                upper = right.low
                gap_pct = (right.low - left.high) / max(left.high, 1e-9)
                invalidated = any(candidate.close < lower for candidate in candles[index + 3:-1])
                invalidation_price = lower * (1.0 - invalidation_buffer_pct)
                active = current.close >= invalidation_price
            else:
                if right.high >= left.low:
                    continue
                lower = right.high
                upper = left.low
                gap_pct = (left.low - right.high) / max(right.high, 1e-9)
                invalidated = any(candidate.close > upper for candidate in candles[index + 3:-1])
                invalidation_price = upper * (1.0 + invalidation_buffer_pct)
                active = current.close <= invalidation_price

            if gap_pct < gap_threshold_pct or invalidated:
                continue

            retested = zone_retested(
                current,
                lower=lower,
                upper=upper,
                tolerance_pct=retest_tolerance_pct,
                direction=direction,
            )
            facts = (
                ExplainItem(label="detector.fvg.lower", value=lower),
                ExplainItem(label="detector.fvg.upper", value=upper),
                ExplainItem(label="detector.fvg.gap_pct", value=gap_pct),
                ExplainItem(label="detector.fvg.retested", value=retested),
                ExplainItem(label="detector.fvg.invalidation_price", value=invalidation_price),
                ExplainItem(label="detector.fvg.body_ratio", value=body_ratio),
                ExplainItem(label="detector.fvg.body_pct", value=body_pct),
            )
            zone = FairValueGapZone(
                structure_id=build_structure_id(
                    self.detector_id,
                    symbol=context.symbol,
                    timeframe=context.timeframe,
                    formed_at=right.candle_start,
                    direction=direction,
                ),
                kind="fair_value_gap",
                symbol=context.symbol,
                timeframe=context.timeframe,
                direction=direction,
                formed_at=right.candle_start,
                invalidated_at=None,
                confidence=min(1.0, gap_pct / max(gap_threshold_pct, 1e-9)),
                lower=lower,
                upper=upper,
                midpoint=(lower + upper) / 2.0,
                invalidation_price=invalidation_price,
                retested=retested,
                active=active,
                left_candle_at=left.candle_start,
                middle_candle_at=middle.candle_start,
                right_candle_at=right.candle_start,
                gap_pct=gap_pct,
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
