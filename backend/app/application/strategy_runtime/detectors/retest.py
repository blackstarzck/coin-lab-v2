from __future__ import annotations

from app.domain.strategy_runtime import DetectorResult, ExplainItem, PriceZone, RetestEvaluation, StructureBreak

from .base import DetectorContext, StructureDetector, build_structure_id, resolve_candles, timeframe_missing_result
from .shared import is_confirmation_candle, zone_retested


class RetestDetector(StructureDetector[RetestEvaluation]):
    detector_id = "retest"

    def required_history(self, config: dict[str, object]) -> int:
        return 1

    def evaluate(self, context: DetectorContext) -> DetectorResult[RetestEvaluation]:
        target = context.config.get("target")
        tolerance_pct = float(context.config.get("tolerance_pct", 0.0015))
        require_rejection_candle = bool(context.config.get("require_rejection_candle", True))
        zone_kind = str(context.config.get("zone_kind", getattr(target, "kind", "unknown")))
        parameters = (
            ExplainItem(label="detector.retest.zone_kind", value=zone_kind),
            ExplainItem(label="detector.retest.tolerance_pct", value=tolerance_pct),
            ExplainItem(label="detector.retest.require_rejection_candle", value=require_rejection_candle),
        )

        candles = resolve_candles(context.snapshot, context.timeframe)
        if not candles:
            return timeframe_missing_result(self.detector_id, parameters=parameters)
        current = candles[-1]

        if isinstance(target, PriceZone):
            direction = target.direction or str(context.config.get("direction", "bullish"))
            lower = target.lower
            upper = target.upper
            touched = zone_retested(
                current,
                lower=lower,
                upper=upper,
                tolerance_pct=tolerance_pct,
                direction=direction,
            )
            retest_price = current.low if direction == "bullish" else current.high
        elif isinstance(target, StructureBreak):
            direction = target.direction or str(context.config.get("direction", "bullish"))
            reference_price = target.reference_price if target.reference_price is not None else target.break_price
            if reference_price is None:
                return DetectorResult(
                    detector_id=self.detector_id,
                    ready=False,
                    matched=False,
                    reason_codes=("DETECTOR_TARGET_INVALID",),
                    parameters=parameters,
                )
            lower = reference_price
            upper = reference_price
            if direction == "bullish":
                touched = current.low <= reference_price * (1.0 + tolerance_pct) and current.close >= reference_price
                retest_price = current.low
            else:
                touched = current.high >= reference_price * (1.0 - tolerance_pct) and current.close <= reference_price
                retest_price = current.high
        else:
            return DetectorResult(
                detector_id=self.detector_id,
                ready=False,
                matched=False,
                reason_codes=("DETECTOR_TARGET_MISSING",),
                parameters=parameters,
            )

        rejection_confirmed = touched and (
            is_confirmation_candle(current, direction=direction) if require_rejection_candle else True
        )
        accepted = touched and rejection_confirmed
        facts = (
            ExplainItem(label="detector.retest.zone_kind", value=zone_kind),
            ExplainItem(label="detector.retest.zone_lower", value=lower),
            ExplainItem(label="detector.retest.zone_upper", value=upper),
            ExplainItem(label="detector.retest.retest_price", value=retest_price),
            ExplainItem(label="detector.retest.accepted", value=accepted),
            ExplainItem(label="detector.retest.rejection_confirmed", value=rejection_confirmed),
        )
        evaluation = RetestEvaluation(
            structure_id=build_structure_id(
                self.detector_id,
                symbol=context.symbol,
                timeframe=context.timeframe,
                formed_at=current.candle_start,
                direction=direction,
            ),
            kind="retest_evaluation",
            symbol=context.symbol,
            timeframe=context.timeframe,
            direction=direction,
            formed_at=current.candle_start,
            invalidated_at=None,
            confidence=1.0 if accepted else 0.0,
            zone_kind=zone_kind,
            zone_lower=lower,
            zone_upper=upper,
            retest_price=retest_price,
            accepted=accepted,
            rejection_confirmed=rejection_confirmed,
            facts=facts,
            reason_codes=("DETECTOR_MATCHED",) if accepted else ("DETECTOR_NO_MATCH",),
        )
        return DetectorResult(
            detector_id=self.detector_id,
            ready=True,
            matched=accepted,
            items=(evaluation,),
            primary=evaluation,
            reason_codes=("DETECTOR_MATCHED",) if accepted else ("DETECTOR_NO_MATCH",),
            facts=facts,
            parameters=parameters,
        )
