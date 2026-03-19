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


class TrendContextDetector(StructureDetector[TrendContext]):
    detector_id = "trend_context"

    def required_history(self, config: dict[str, object]) -> int:
        lookback = int(config.get("lookback", 12))
        return max(lookback, 2)

    def evaluate(self, context: DetectorContext) -> DetectorResult[TrendContext]:
        direction = str(context.config.get("direction", "bullish")).strip().lower()
        lookback = int(context.config.get("lookback", 12))
        parameters = (
            ExplainItem(label="detector.trend_context.direction", value=direction),
            ExplainItem(label="detector.trend_context.lookback", value=lookback),
        )
        candles = resolve_candles(context.snapshot, context.timeframe)
        if not candles:
            return timeframe_missing_result(self.detector_id, parameters=parameters)
        if len(candles) < self.required_history(context.config):
            return history_not_ready_result(
                self.detector_id,
                facts=(ExplainItem(label="detector.trend_context.history_size", value=len(candles)),),
                parameters=parameters,
            )

        window = candles[-lookback:]
        midpoint = max(lookback // 2, 1)
        early = window[:midpoint]
        late = window[midpoint:]

        early_support = min(candle.low for candle in early)
        late_support = min(candle.low for candle in late)
        early_resistance = max(candle.high for candle in early)
        late_resistance = max(candle.high for candle in late)
        average_close = sum(candle.close for candle in window) / len(window)
        latest_close = window[-1].close
        start_close = window[0].close

        bullish = (
            latest_close > start_close
            and latest_close >= average_close
            and late_support >= early_support
            and late_resistance >= early_resistance
        )
        bearish = (
            latest_close < start_close
            and latest_close <= average_close
            and late_support <= early_support
            and late_resistance <= early_resistance
        )
        if bullish:
            trend_state = "trend_up"
            trend_direction = "bullish"
        elif bearish:
            trend_state = "trend_down"
            trend_direction = "bearish"
        else:
            trend_state = "range"
            trend_direction = None

        facts = (
            ExplainItem(label="detector.trend_context.start_close", value=start_close),
            ExplainItem(label="detector.trend_context.latest_close", value=latest_close),
            ExplainItem(label="detector.trend_context.average_close", value=average_close),
            ExplainItem(label="detector.trend_context.support", value=late_support),
            ExplainItem(label="detector.trend_context.resistance", value=late_resistance),
            ExplainItem(label="detector.trend_context.trend_state", value=trend_state),
        )
        matched = trend_state == _direction_to_state(direction)
        reason_codes = ("DETECTOR_MATCHED",) if matched else ("DETECTOR_NO_MATCH",)
        confidence = min(1.0, abs(latest_close - start_close) / max(abs(average_close), 1e-9) * 4.0)
        trend = TrendContext(
            structure_id=build_structure_id(
                self.detector_id,
                symbol=context.symbol,
                timeframe=context.timeframe,
                formed_at=window[0].candle_start,
                direction=trend_direction,
            ),
            kind="trend_context",
            symbol=context.symbol,
            timeframe=context.timeframe,
            direction=trend_direction,
            formed_at=window[0].candle_start,
            invalidated_at=None,
            confidence=confidence,
            support=late_support,
            resistance=late_resistance,
            average_close=average_close,
            start_close=start_close,
            latest_close=latest_close,
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
