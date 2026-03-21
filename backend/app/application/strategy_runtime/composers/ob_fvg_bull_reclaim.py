from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.strategy_runtime.detectors import DetectorContext, SwingTrendContextDetector, resolve_candles
from app.application.strategy_runtime.detectors.shared import average_true_range, candle_body_metrics
from app.domain.entities.market import CandleState
from app.domain.strategy_runtime import EntrySetup, ExplainItem, RiskEnvelope, SetupConfluence, StrategyDecisionDraft, TrendContext

from .base import ComposerContext, StrategyComposer


@dataclass(slots=True, frozen=True)
class PoiSignal:
    formed_index: int
    zone_low: float
    zone_high: float
    ob_low: float
    expires_index: int
    formed_at: datetime
    impulse_range: float
    impulse_atr: float


class ObFvgBullReclaimComposer(StrategyComposer):
    composer_id = "ob_fvg_bull_reclaim_v1"

    def __init__(self) -> None:
        self._swing_trend_detector = SwingTrendContextDetector()

    def validate(self, config: dict[str, object]) -> None:
        entry_timeframe = config.get("timeframe", config.get("entry_timeframe", "15m"))
        trend_timeframe = config.get("trend_timeframe", "1h")
        swing_width = config.get("swing_width", 3)
        atr_length = config.get("atr_length", 14)
        atr_mult = config.get("atr_mult", 1.8)
        body_ratio_threshold = config.get("body_ratio_threshold", 0.45)
        ob_lookback = config.get("ob_lookback", 8)
        poi_expiry_bars = config.get("poi_expiry_bars", 24)
        sl_buffer_pct = config.get("sl_buffer_pct", 0.001)
        rr_target = config.get("rr_target", 1.8)
        require_prev_close = config.get("require_prev_close", False)
        bull_mode_off_exit_on_loss = config.get("bull_mode_off_exit_on_loss", True)

        if not isinstance(entry_timeframe, str) or not entry_timeframe.strip():
            raise ValueError("timeframe must be a non-empty string")
        if not isinstance(trend_timeframe, str) or not trend_timeframe.strip():
            raise ValueError("trend_timeframe must be a non-empty string")
        if not isinstance(swing_width, int) or swing_width < 1:
            raise ValueError("swing_width must be an integer greater than or equal to 1")
        if not isinstance(atr_length, int) or atr_length < 2:
            raise ValueError("atr_length must be an integer greater than or equal to 2")
        if not isinstance(atr_mult, (int, float)) or float(atr_mult) <= 0.0:
            raise ValueError("atr_mult must be a positive number")
        if not isinstance(body_ratio_threshold, (int, float)) or not 0.0 < float(body_ratio_threshold) <= 1.0:
            raise ValueError("body_ratio_threshold must be a number between 0 and 1")
        if not isinstance(ob_lookback, int) or ob_lookback < 1:
            raise ValueError("ob_lookback must be an integer greater than or equal to 1")
        if not isinstance(poi_expiry_bars, int) or poi_expiry_bars < 1:
            raise ValueError("poi_expiry_bars must be an integer greater than or equal to 1")
        if not isinstance(sl_buffer_pct, (int, float)) or float(sl_buffer_pct) < 0.0:
            raise ValueError("sl_buffer_pct must be a non-negative number")
        if not isinstance(rr_target, (int, float)) or float(rr_target) <= 0.0:
            raise ValueError("rr_target must be a positive number")
        if not isinstance(require_prev_close, bool):
            raise ValueError("require_prev_close must be a boolean")
        if not isinstance(bull_mode_off_exit_on_loss, bool):
            raise ValueError("bull_mode_off_exit_on_loss must be a boolean")

    def compose(self, context: ComposerContext) -> StrategyDecisionDraft:
        self.validate(context.config)

        entry_timeframe = str(context.config.get("timeframe", context.config.get("entry_timeframe", context.timeframe)))
        trend_timeframe = str(context.config.get("trend_timeframe", "1h"))
        swing_width = int(context.config.get("swing_width", 3))
        atr_length = int(context.config.get("atr_length", 14))
        atr_mult = float(context.config.get("atr_mult", 1.8))
        body_ratio_threshold = float(context.config.get("body_ratio_threshold", 0.45))
        ob_lookback = int(context.config.get("ob_lookback", 8))
        poi_expiry_bars = int(context.config.get("poi_expiry_bars", 24))
        sl_buffer_pct = float(context.config.get("sl_buffer_pct", 0.001))
        rr_target = float(context.config.get("rr_target", 1.8))
        time_exit_bars = int(context.config.get("time_exit_bars", 20))
        require_prev_close = bool(context.config.get("require_prev_close", False))
        bull_mode_off_exit_on_loss = bool(context.config.get("bull_mode_off_exit_on_loss", True))

        entry_candles = resolve_candles(context.snapshot, entry_timeframe)
        trend_candles = resolve_candles(context.snapshot, trend_timeframe)
        parameters = self._parameters(
            entry_timeframe=entry_timeframe,
            trend_timeframe=trend_timeframe,
            swing_width=swing_width,
            atr_length=atr_length,
            atr_mult=atr_mult,
            body_ratio_threshold=body_ratio_threshold,
            ob_lookback=ob_lookback,
            poi_expiry_bars=poi_expiry_bars,
            sl_buffer_pct=sl_buffer_pct,
            rr_target=rr_target,
            time_exit_bars=time_exit_bars,
            require_prev_close=require_prev_close,
            bull_mode_off_exit_on_loss=bull_mode_off_exit_on_loss,
        )

        minimum_entry_history = max(atr_length + 2, ob_lookback + 2, 4)
        minimum_trend_history = self._swing_trend_detector.required_history({"width": swing_width})
        if len(entry_candles) < minimum_entry_history or len(trend_candles) < minimum_trend_history:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(
                    f"composer.{self.composer_id}.{entry_timeframe}.history_ready",
                    f"composer.{self.composer_id}.{trend_timeframe}.history_ready",
                ),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        trend_result = self._swing_trend_detector.evaluate(
            DetectorContext(
                snapshot=context.snapshot,
                symbol=context.symbol,
                timeframe=trend_timeframe,
                config={"direction": "bullish", "width": swing_width},
            )
        )
        trend = trend_result.primary
        if trend is None:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(f"composer.{self.composer_id}.{trend_timeframe}.trend_context_ready",),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        bull_mode_map = self._build_bull_mode_map(entry_candles, trend_candles, swing_width)
        atr_series = average_true_range(entry_candles, atr_length)
        signals = self._build_signals(
            entry_candles=entry_candles,
            bull_mode_map=bull_mode_map,
            atr_series=atr_series,
            atr_mult=atr_mult,
            body_ratio_threshold=body_ratio_threshold,
            ob_lookback=ob_lookback,
            poi_expiry_bars=poi_expiry_bars,
        )
        current = entry_candles[-1]
        current_index = len(entry_candles) - 1
        current_bull_mode_on = bull_mode_map.get(current_index, False)
        matched_signal = self._select_entry_signal(
            signals=signals,
            candles=entry_candles,
            current_index=current_index,
            require_prev_close=require_prev_close,
        )
        facts = self._facts(
            current=current,
            current_index=current_index,
            bull_mode_on=current_bull_mode_on,
            trend=trend,
            active_signal=matched_signal,
            signal_count=len(signals),
        )

        matched_conditions: list[str] = []
        failed_conditions: list[str] = []
        self._append_condition(
            matched_conditions,
            failed_conditions,
            current_bull_mode_on,
            f"composer.{self.composer_id}.trend.bull_mode_on",
        )

        if matched_signal is None:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=trend.confidence or 0.0,
                entry_setup=None,
                exit_setup=None,
                matched_conditions=tuple(matched_conditions),
                failed_conditions=tuple(failed_conditions + [f"composer.{self.composer_id}.entry.poi_touch_confirmation"]),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_HOLD",),
            )

        entry_price = current.close
        stop_loss_price = matched_signal.ob_low * (1.0 - sl_buffer_pct)
        if stop_loss_price >= entry_price:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                matched_conditions=tuple(matched_conditions),
                failed_conditions=(f"composer.{self.composer_id}.risk.stop_below_entry",),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_HOLD",),
            )

        risk_size = entry_price - stop_loss_price
        take_profit_price = entry_price + (risk_size * rr_target)
        matched_conditions.extend(
            (
                f"composer.{self.composer_id}.entry.zone_touch",
                f"composer.{self.composer_id}.entry.bullish_close",
                f"composer.{self.composer_id}.entry.formed_under_bull_mode",
            )
        )
        confluence = SetupConfluence(
            score=4,
            max_score=4,
            matched_conditions=tuple(matched_conditions),
            failed_conditions=tuple(failed_conditions),
            facts=(ExplainItem(label=f"composer.{self.composer_id}.signal_count", value=len(signals)),),
            reason_codes=("PLUGIN_OB_FVG_BULL_RECLAIM_ENTRY",),
        )
        risk = RiskEnvelope(
            invalidation_price=stop_loss_price,
            stop_loss_price=stop_loss_price,
            take_profit_prices=(take_profit_price,),
            trailing_activation_price=None,
            max_holding_bars=time_exit_bars,
        )
        entry_setup = EntrySetup(
            setup_id=f"ob_fvg_entry:{context.symbol}:{entry_timeframe}:{current.candle_start.isoformat()}",
            symbol=context.symbol,
            timeframe=entry_timeframe,
            direction="long",
            setup_type="ob_fvg_bull_reclaim_long",
            valid=True,
            confidence=min(1.0, 0.55 + (trend.confidence or 0.0) * 0.45),
            trigger_price=entry_price,
            preferred_entry_zone=(matched_signal.zone_low, matched_signal.zone_high),
            invalidation_price=stop_loss_price,
            confluence=confluence,
            risk=risk,
            structures=(trend,),
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_OB_FVG_BULL_RECLAIM_ENTRY",),
        )
        return StrategyDecisionDraft(
            action="ENTER",
            confidence=entry_setup.confidence,
            entry_setup=entry_setup,
            exit_setup=None,
            matched_conditions=tuple(matched_conditions),
            failed_conditions=tuple(failed_conditions),
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_OB_FVG_BULL_RECLAIM_ENTRY",),
        )

    def _build_bull_mode_map(
        self,
        entry_candles: list[CandleState],
        trend_candles: list[CandleState],
        swing_width: int,
    ) -> dict[int, bool]:
        swing_lows, swing_highs = self._swing_trend_detector._find_swings(trend_candles, swing_width)  # noqa: SLF001
        bull_by_trend_index: dict[int, bool] = {}
        for trend_index, _ in enumerate(trend_candles):
            prior_lows = [index for index in swing_lows if index < trend_index]
            prior_highs = [index for index in swing_highs if index < trend_index]
            bull_mode_on = False
            if len(prior_lows) >= 2 and len(prior_highs) >= 2:
                bull_mode_on = (
                    trend_candles[prior_lows[-1]].low > trend_candles[prior_lows[-2]].low
                    and trend_candles[prior_highs[-1]].high > trend_candles[prior_highs[-2]].high
                )
            bull_by_trend_index[trend_index] = bull_mode_on

        trend_span = self._timeframe_delta(trend_candles[0].timeframe if trend_candles else "1h")
        bull_mode_map: dict[int, bool] = {}
        for entry_index, candle in enumerate(entry_candles):
            active_index = -1
            for trend_index, trend_candle in enumerate(trend_candles):
                if trend_candle.candle_start + trend_span <= candle.candle_start:
                    active_index = trend_index
                else:
                    break
            bull_mode_map[entry_index] = bull_by_trend_index.get(active_index, False)
        return bull_mode_map

    def _build_signals(
        self,
        *,
        entry_candles: list[CandleState],
        bull_mode_map: dict[int, bool],
        atr_series: list[float | None],
        atr_mult: float,
        body_ratio_threshold: float,
        ob_lookback: int,
        poi_expiry_bars: int,
    ) -> list[PoiSignal]:
        signals: list[PoiSignal] = []
        for index in range(2, len(entry_candles)):
            left = entry_candles[index - 2]
            middle = entry_candles[index - 1]
            right = entry_candles[index]
            atr_value = atr_series[index - 1]
            if atr_value is None or not bull_mode_map.get(index, False):
                continue

            candle_range, body_ratio, _ = candle_body_metrics(middle)
            impulse_ok = (
                middle.close > middle.open
                and candle_range > atr_value * atr_mult
                and body_ratio >= body_ratio_threshold
            )
            bullish_fvg = right.low > left.high
            if not (impulse_ok and bullish_fvg):
                continue

            recent = entry_candles[max(0, index - ob_lookback) : index]
            bearish_candles = [candle for candle in recent if candle.close < candle.open]
            if not bearish_candles:
                continue
            order_block = bearish_candles[-1]
            signals.append(
                PoiSignal(
                    formed_index=index,
                    zone_low=left.high,
                    zone_high=right.low,
                    ob_low=order_block.low,
                    expires_index=min(len(entry_candles) - 1, index + poi_expiry_bars),
                    formed_at=right.candle_start,
                    impulse_range=candle_range,
                    impulse_atr=atr_value,
                )
            )
        return signals

    def _select_entry_signal(
        self,
        *,
        signals: list[PoiSignal],
        candles: list[CandleState],
        current_index: int,
        require_prev_close: bool,
    ) -> PoiSignal | None:
        current = candles[current_index]
        bullish_close = current.close > current.open
        if require_prev_close and current_index > 0:
            bullish_close = bullish_close and current.close >= candles[current_index - 1].close
        if not bullish_close:
            return None

        for signal in signals:
            if signal.formed_index > current_index or signal.expires_index < current_index:
                continue
            touched = current.low <= signal.zone_high and current.high >= signal.zone_low
            if touched:
                return signal
        return None

    def _parameters(
        self,
        *,
        entry_timeframe: str,
        trend_timeframe: str,
        swing_width: int,
        atr_length: int,
        atr_mult: float,
        body_ratio_threshold: float,
        ob_lookback: int,
        poi_expiry_bars: int,
        sl_buffer_pct: float,
        rr_target: float,
        time_exit_bars: int,
        require_prev_close: bool,
        bull_mode_off_exit_on_loss: bool,
    ) -> tuple[ExplainItem, ...]:
        return (
            ExplainItem(label=f"composer.{self.composer_id}.entry_timeframe", value=entry_timeframe),
            ExplainItem(label=f"composer.{self.composer_id}.trend_timeframe", value=trend_timeframe),
            ExplainItem(label=f"composer.{self.composer_id}.swing_width", value=swing_width),
            ExplainItem(label=f"composer.{self.composer_id}.atr_length", value=atr_length),
            ExplainItem(label=f"composer.{self.composer_id}.atr_mult", value=atr_mult),
            ExplainItem(label=f"composer.{self.composer_id}.body_ratio_threshold", value=body_ratio_threshold),
            ExplainItem(label=f"composer.{self.composer_id}.ob_lookback", value=ob_lookback),
            ExplainItem(label=f"composer.{self.composer_id}.poi_expiry_bars", value=poi_expiry_bars),
            ExplainItem(label=f"composer.{self.composer_id}.sl_buffer_pct", value=sl_buffer_pct),
            ExplainItem(label=f"composer.{self.composer_id}.rr_target", value=rr_target),
            ExplainItem(label=f"composer.{self.composer_id}.time_exit_bars", value=time_exit_bars),
            ExplainItem(label=f"composer.{self.composer_id}.require_prev_close", value=require_prev_close),
            ExplainItem(label=f"composer.{self.composer_id}.bull_mode_off_exit_on_loss", value=bull_mode_off_exit_on_loss),
        )

    def _facts(
        self,
        *,
        current: CandleState,
        current_index: int,
        bull_mode_on: bool,
        trend: TrendContext,
        active_signal: PoiSignal | None,
        signal_count: int,
    ) -> tuple[ExplainItem, ...]:
        facts = [
            ExplainItem(label=f"{current.timeframe}.close", value=current.close),
            ExplainItem(label=f"{current.timeframe}.high", value=current.high),
            ExplainItem(label=f"{current.timeframe}.low", value=current.low),
            ExplainItem(label=f"composer.{self.composer_id}.current_index", value=current_index),
            ExplainItem(label=f"composer.{self.composer_id}.bull_mode_on", value=bull_mode_on),
            ExplainItem(label=f"composer.{self.composer_id}.signal_count", value=signal_count),
            ExplainItem(label=f"composer.{self.composer_id}.trend_state", value=trend.trend_state),
            ExplainItem(label=f"composer.{self.composer_id}.trend_support", value=trend.support),
            ExplainItem(label=f"composer.{self.composer_id}.trend_resistance", value=trend.resistance),
        ]
        if active_signal is not None:
            facts.extend(
                (
                    ExplainItem(label=f"composer.{self.composer_id}.signal.formed_index", value=active_signal.formed_index),
                    ExplainItem(label=f"composer.{self.composer_id}.signal.zone_low", value=active_signal.zone_low),
                    ExplainItem(label=f"composer.{self.composer_id}.signal.zone_high", value=active_signal.zone_high),
                    ExplainItem(label=f"composer.{self.composer_id}.signal.ob_low", value=active_signal.ob_low),
                    ExplainItem(label=f"composer.{self.composer_id}.signal.expires_index", value=active_signal.expires_index),
                    ExplainItem(label=f"composer.{self.composer_id}.signal.impulse_range", value=active_signal.impulse_range),
                    ExplainItem(label=f"composer.{self.composer_id}.signal.impulse_atr", value=active_signal.impulse_atr),
                )
            )
        return tuple(facts)

    def _append_condition(
        self,
        matched_conditions: list[str],
        failed_conditions: list[str],
        condition_met: bool,
        label: str,
    ) -> None:
        if condition_met:
            matched_conditions.append(label)
        else:
            failed_conditions.append(label)

    def _timeframe_delta(self, timeframe: str) -> timedelta:
        normalized = timeframe.strip().lower()
        if normalized.endswith("m"):
            return timedelta(minutes=int(normalized[:-1]))
        if normalized.endswith("h"):
            return timedelta(hours=int(normalized[:-1]))
        if normalized.endswith("d"):
            return timedelta(days=int(normalized[:-1]))
        raise ValueError(f"unsupported timeframe: {timeframe}")
