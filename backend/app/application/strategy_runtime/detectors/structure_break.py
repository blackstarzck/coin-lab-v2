from __future__ import annotations

from app.domain.strategy_runtime import DetectorResult, ExplainItem, StructureBreak

from .base import (
    DetectorContext,
    StructureDetector,
    build_structure_id,
    history_not_ready_result,
    resolve_candles,
    timeframe_missing_result,
)


class StructureBreakDetector(StructureDetector[StructureBreak]):
    detector_id = "structure_break"

    def required_history(self, config: dict[str, object]) -> int:
        swing_lookback = int(config.get("swing_lookback", 5))
        return max((swing_lookback * 2) + 1, 6)

    def evaluate(self, context: DetectorContext) -> DetectorResult[StructureBreak]:
        swing_lookback = int(context.config.get("swing_lookback", 5))
        break_confirmation = str(context.config.get("break_confirmation", "close")).strip().lower()
        break_buffer_pct = float(context.config.get("break_buffer_pct", 0.0))
        direction_filter = str(context.config.get("direction", "both")).strip().lower()
        parameters = (
            ExplainItem(label="detector.structure_break.swing_lookback", value=swing_lookback),
            ExplainItem(label="detector.structure_break.break_confirmation", value=break_confirmation),
            ExplainItem(label="detector.structure_break.break_buffer_pct", value=break_buffer_pct),
            ExplainItem(label="detector.structure_break.direction", value=direction_filter),
        )

        candles = resolve_candles(context.snapshot, context.timeframe)
        if not candles:
            return timeframe_missing_result(self.detector_id, parameters=parameters)
        if len(candles) < self.required_history(context.config):
            return history_not_ready_result(
                self.detector_id,
                facts=(ExplainItem(label="detector.structure_break.history_size", value=len(candles)),),
                parameters=parameters,
            )

        current = candles[-1]
        prior_window = candles[-((swing_lookback * 2) + 1):-swing_lookback - 1]
        reference_window = candles[-swing_lookback - 1:-1]

        prior_start_close = prior_window[0].close
        prior_end_close = prior_window[-1].close
        if prior_end_close > prior_start_close:
            prior_direction = "bullish"
        elif prior_end_close < prior_start_close:
            prior_direction = "bearish"
        else:
            prior_direction = "range"

        if break_confirmation == "close":
            bullish_reference = max(candle.close for candle in reference_window)
            bearish_reference = min(candle.close for candle in reference_window)
            bullish_break_price = current.close
            bearish_break_price = current.close
        else:
            bullish_reference = max(candle.high for candle in reference_window)
            bearish_reference = min(candle.low for candle in reference_window)
            bullish_break_price = current.high
            bearish_break_price = current.low

        bullish_confirmed = bullish_break_price > bullish_reference * (1.0 + break_buffer_pct)
        bearish_confirmed = bearish_break_price < bearish_reference * (1.0 - break_buffer_pct)

        if direction_filter == "bullish":
            bearish_confirmed = False
        elif direction_filter == "bearish":
            bullish_confirmed = False

        if bullish_confirmed and not bearish_confirmed:
            direction = "bullish"
            reference_price = bullish_reference
            break_price = bullish_break_price
            break_type = "bos" if prior_direction in {"bullish", "range"} else "choch"
        elif bearish_confirmed and not bullish_confirmed:
            direction = "bearish"
            reference_price = bearish_reference
            break_price = bearish_break_price
            break_type = "bos" if prior_direction in {"bearish", "range"} else "choch"
        else:
            return DetectorResult(
                detector_id=self.detector_id,
                ready=True,
                matched=False,
                reason_codes=("DETECTOR_NO_MATCH",),
                facts=(ExplainItem(label="detector.structure_break.prior_direction", value=prior_direction),),
                parameters=parameters,
            )

        distance = abs(break_price - reference_price) / max(abs(reference_price), 1e-9)
        facts = (
            ExplainItem(label="detector.structure_break.break_type", value=break_type),
            ExplainItem(label="detector.structure_break.reference_price", value=reference_price),
            ExplainItem(label="detector.structure_break.break_price", value=break_price),
            ExplainItem(label="detector.structure_break.confirmed", value=True),
            ExplainItem(label="detector.structure_break.prior_direction", value=prior_direction),
        )
        structure = StructureBreak(
            structure_id=build_structure_id(
                self.detector_id,
                symbol=context.symbol,
                timeframe=context.timeframe,
                formed_at=current.candle_start,
                direction=direction,
            ),
            kind="structure_break",
            symbol=context.symbol,
            timeframe=context.timeframe,
            direction=direction,
            formed_at=current.candle_start,
            invalidated_at=None,
            confidence=min(1.0, distance / max(break_buffer_pct or 0.0025, 0.0025)),
            break_type=break_type,
            reference_price=reference_price,
            break_price=break_price,
            confirmed=True,
            facts=facts,
            reason_codes=("DETECTOR_MATCHED",),
        )
        return DetectorResult(
            detector_id=self.detector_id,
            ready=True,
            matched=True,
            items=(structure,),
            primary=structure,
            reason_codes=("DETECTOR_MATCHED",),
            facts=facts,
            parameters=parameters,
        )
