from __future__ import annotations

from app.application.strategy_runtime.detectors import DetectorContext, SwingTrendContextDetector, TrendContextDetector, average_true_range, resolve_candles
from app.domain.strategy_runtime import EntrySetup, ExitSetup, ExplainItem, RiskEnvelope, SetupConfluence, StrategyDecisionDraft, TrendContext

from .base import ComposerContext, StrategyComposer


class ZenithHazelComposer(StrategyComposer):
    composer_id = "zenith_hazel_v1"

    def __init__(self) -> None:
        self._trend_detector = TrendContextDetector()
        self._swing_detector = SwingTrendContextDetector()

    def validate(self, config: dict[str, object]) -> None:
        timeframe = config.get("timeframe", "15m")
        regime_timeframe = config.get("regime_timeframe", "1h")
        regime_lookback = config.get("regime_lookback", 12)
        swing_width = config.get("swing_width", 3)
        breakout_lookback = config.get("breakout_lookback", 20)
        momentum_lookback = config.get("momentum_lookback", 6)
        ema_fast_length = config.get("ema_fast_length", 9)
        ema_slow_length = config.get("ema_slow_length", 21)
        atr_length = config.get("atr_length", 14)
        min_regime_confidence = config.get("min_regime_confidence", 0.2)
        min_signal_confidence = config.get("min_signal_confidence", 0.7)
        min_signal_score = config.get("min_signal_score", 4)
        breakout_buffer_pct = config.get("breakout_buffer_pct", 0.001)
        min_momentum_pct = config.get("min_momentum_pct", 0.004)
        volume_surge_ratio = config.get("volume_surge_ratio", 1.2)
        min_close_strength = config.get("min_close_strength", 0.6)
        high_volatility_atr_pct = config.get("high_volatility_atr_pct", 0.03)
        stop_buffer_pct = config.get("stop_buffer_pct", 0.002)
        exit_breakdown_pct = config.get("exit_breakdown_pct", 0.005)
        rr_target = config.get("rr_target", 2.0)
        time_exit_bars = config.get("time_exit_bars", 24)
        allow_high_volatility_breakout = config.get("allow_high_volatility_breakout", False)

        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("timeframe must be a non-empty string")
        if not isinstance(regime_timeframe, str) or not regime_timeframe.strip():
            raise ValueError("regime_timeframe must be a non-empty string")
        if not isinstance(regime_lookback, int) or regime_lookback < 6:
            raise ValueError("regime_lookback must be an integer greater than or equal to 6")
        if not isinstance(swing_width, int) or swing_width < 1:
            raise ValueError("swing_width must be an integer greater than or equal to 1")
        if not isinstance(breakout_lookback, int) or breakout_lookback < 3:
            raise ValueError("breakout_lookback must be an integer greater than or equal to 3")
        if not isinstance(momentum_lookback, int) or momentum_lookback < 2:
            raise ValueError("momentum_lookback must be an integer greater than or equal to 2")
        if not isinstance(ema_fast_length, int) or ema_fast_length < 2:
            raise ValueError("ema_fast_length must be an integer greater than or equal to 2")
        if not isinstance(ema_slow_length, int) or ema_slow_length <= int(ema_fast_length):
            raise ValueError("ema_slow_length must be greater than ema_fast_length")
        if not isinstance(atr_length, int) or atr_length < 2:
            raise ValueError("atr_length must be an integer greater than or equal to 2")
        if not isinstance(min_regime_confidence, (int, float)) or not 0.0 <= float(min_regime_confidence) <= 1.0:
            raise ValueError("min_regime_confidence must be a number between 0 and 1")
        if not isinstance(min_signal_confidence, (int, float)) or not 0.0 <= float(min_signal_confidence) <= 1.0:
            raise ValueError("min_signal_confidence must be a number between 0 and 1")
        if not isinstance(min_signal_score, int) or not 1 <= min_signal_score <= 5:
            raise ValueError("min_signal_score must be an integer between 1 and 5")
        if not isinstance(breakout_buffer_pct, (int, float)) or float(breakout_buffer_pct) < 0.0:
            raise ValueError("breakout_buffer_pct must be a non-negative number")
        if not isinstance(min_momentum_pct, (int, float)) or float(min_momentum_pct) < 0.0:
            raise ValueError("min_momentum_pct must be a non-negative number")
        if not isinstance(volume_surge_ratio, (int, float)) or float(volume_surge_ratio) < 1.0:
            raise ValueError("volume_surge_ratio must be a number greater than or equal to 1")
        if not isinstance(min_close_strength, (int, float)) or not 0.0 <= float(min_close_strength) <= 1.0:
            raise ValueError("min_close_strength must be a number between 0 and 1")
        if not isinstance(high_volatility_atr_pct, (int, float)) or float(high_volatility_atr_pct) < 0.0:
            raise ValueError("high_volatility_atr_pct must be a non-negative number")
        if not isinstance(stop_buffer_pct, (int, float)) or float(stop_buffer_pct) < 0.0:
            raise ValueError("stop_buffer_pct must be a non-negative number")
        if not isinstance(exit_breakdown_pct, (int, float)) or float(exit_breakdown_pct) < 0.0:
            raise ValueError("exit_breakdown_pct must be a non-negative number")
        if not isinstance(rr_target, (int, float)) or float(rr_target) <= 0.0:
            raise ValueError("rr_target must be a positive number")
        if not isinstance(time_exit_bars, int) or time_exit_bars < 1:
            raise ValueError("time_exit_bars must be an integer greater than or equal to 1")
        if not isinstance(allow_high_volatility_breakout, bool):
            raise ValueError("allow_high_volatility_breakout must be a boolean")

    def compose(self, context: ComposerContext) -> StrategyDecisionDraft:
        self.validate(context.config)

        timeframe = str(context.config.get("timeframe", context.timeframe))
        regime_timeframe = str(context.config.get("regime_timeframe", "1h"))
        regime_lookback = int(context.config.get("regime_lookback", 12))
        swing_width = int(context.config.get("swing_width", 3))
        breakout_lookback = int(context.config.get("breakout_lookback", 20))
        momentum_lookback = int(context.config.get("momentum_lookback", 6))
        ema_fast_length = int(context.config.get("ema_fast_length", 9))
        ema_slow_length = int(context.config.get("ema_slow_length", 21))
        atr_length = int(context.config.get("atr_length", 14))
        min_regime_confidence = float(context.config.get("min_regime_confidence", 0.2))
        min_signal_confidence = float(context.config.get("min_signal_confidence", 0.7))
        min_signal_score = int(context.config.get("min_signal_score", 4))
        breakout_buffer_pct = float(context.config.get("breakout_buffer_pct", 0.001))
        min_momentum_pct = float(context.config.get("min_momentum_pct", 0.004))
        volume_surge_ratio = float(context.config.get("volume_surge_ratio", 1.2))
        min_close_strength = float(context.config.get("min_close_strength", 0.6))
        high_volatility_atr_pct = float(context.config.get("high_volatility_atr_pct", 0.03))
        stop_buffer_pct = float(context.config.get("stop_buffer_pct", 0.002))
        exit_breakdown_pct = float(context.config.get("exit_breakdown_pct", 0.005))
        rr_target = float(context.config.get("rr_target", 2.0))
        time_exit_bars = int(context.config.get("time_exit_bars", 24))
        allow_high_volatility_breakout = bool(context.config.get("allow_high_volatility_breakout", False))

        candles = resolve_candles(context.snapshot, timeframe)
        regime_candles = resolve_candles(context.snapshot, regime_timeframe)
        parameters = (
            ExplainItem(label=f"composer.{self.composer_id}.timeframe", value=timeframe),
            ExplainItem(label=f"composer.{self.composer_id}.regime_timeframe", value=regime_timeframe),
            ExplainItem(label=f"composer.{self.composer_id}.regime_lookback", value=regime_lookback),
            ExplainItem(label=f"composer.{self.composer_id}.swing_width", value=swing_width),
            ExplainItem(label=f"composer.{self.composer_id}.breakout_lookback", value=breakout_lookback),
            ExplainItem(label=f"composer.{self.composer_id}.momentum_lookback", value=momentum_lookback),
            ExplainItem(label=f"composer.{self.composer_id}.ema_fast_length", value=ema_fast_length),
            ExplainItem(label=f"composer.{self.composer_id}.ema_slow_length", value=ema_slow_length),
            ExplainItem(label=f"composer.{self.composer_id}.atr_length", value=atr_length),
            ExplainItem(label=f"composer.{self.composer_id}.min_regime_confidence", value=min_regime_confidence),
            ExplainItem(label=f"composer.{self.composer_id}.min_signal_confidence", value=min_signal_confidence),
            ExplainItem(label=f"composer.{self.composer_id}.min_signal_score", value=min_signal_score),
            ExplainItem(label=f"composer.{self.composer_id}.breakout_buffer_pct", value=breakout_buffer_pct),
            ExplainItem(label=f"composer.{self.composer_id}.min_momentum_pct", value=min_momentum_pct),
            ExplainItem(label=f"composer.{self.composer_id}.volume_surge_ratio", value=volume_surge_ratio),
            ExplainItem(label=f"composer.{self.composer_id}.min_close_strength", value=min_close_strength),
            ExplainItem(label=f"composer.{self.composer_id}.high_volatility_atr_pct", value=high_volatility_atr_pct),
            ExplainItem(label=f"composer.{self.composer_id}.stop_buffer_pct", value=stop_buffer_pct),
            ExplainItem(label=f"composer.{self.composer_id}.exit_breakdown_pct", value=exit_breakdown_pct),
            ExplainItem(label=f"composer.{self.composer_id}.rr_target", value=rr_target),
            ExplainItem(label=f"composer.{self.composer_id}.time_exit_bars", value=time_exit_bars),
            ExplainItem(label=f"composer.{self.composer_id}.allow_high_volatility_breakout", value=allow_high_volatility_breakout),
        )

        minimum_history = max(breakout_lookback + 2, momentum_lookback + 2, ema_slow_length + 1, atr_length + 1, 8)
        minimum_regime_history = max(
            self._trend_detector.required_history({"lookback": regime_lookback}),
            self._swing_detector.required_history({"width": swing_width}),
        )
        if len(candles) < minimum_history or len(regime_candles) < minimum_regime_history:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(
                    f"composer.{self.composer_id}.{timeframe}.history_ready",
                    f"composer.{self.composer_id}.{regime_timeframe}.history_ready",
                ),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        trend_result = self._trend_detector.evaluate(
            DetectorContext(
                snapshot=context.snapshot,
                symbol=context.symbol,
                timeframe=regime_timeframe,
                config={"direction": "bullish", "lookback": regime_lookback},
            )
        )
        swing_result = self._swing_detector.evaluate(
            DetectorContext(
                snapshot=context.snapshot,
                symbol=context.symbol,
                timeframe=regime_timeframe,
                config={"direction": "bullish", "width": swing_width},
            )
        )
        trend = trend_result.primary
        swing = swing_result.primary
        if trend is None or swing is None:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(f"composer.{self.composer_id}.{regime_timeframe}.regime_ready",),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        atr_series = average_true_range(candles, atr_length)
        atr_value = atr_series[-1]
        if atr_value is None:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(f"composer.{self.composer_id}.{timeframe}.atr_ready",),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        current = candles[-1]
        breakout_window = candles[-breakout_lookback - 1 : -1]
        momentum_base = candles[-momentum_lookback - 1].close
        average_volume = sum(candle.volume for candle in breakout_window) / max(len(breakout_window), 1)
        ema_fast = self._ema([candle.close for candle in candles], ema_fast_length)
        ema_slow = self._ema([candle.close for candle in candles], ema_slow_length)
        breakout_level = max(candle.high for candle in breakout_window)
        fallback_floor = min(candle.low for candle in breakout_window)
        support_price = min(candle.low for candle in candles[-max(momentum_lookback + 1, 6) :])
        momentum_pct = (current.close / momentum_base) - 1.0 if momentum_base > 0 else 0.0
        volume_ratio = current.volume / max(average_volume, 1e-9)
        candle_range = max(current.high - current.low, 0.0)
        close_strength = (current.close - current.low) / candle_range if candle_range > 0 else 0.0
        atr_pct = atr_value / max(abs(current.close), 1e-9)

        regime_state, regime_label, regime_confidence = self._classify_regime(
            trend=trend,
            swing=swing,
            atr_pct=atr_pct,
            min_regime_confidence=min_regime_confidence,
            high_volatility_atr_pct=high_volatility_atr_pct,
        )
        regime_entry_allowed = regime_state == "trend_up" or (allow_high_volatility_breakout and regime_state == "high_volatility")
        trend_alignment = current.close >= ema_fast and ema_fast >= ema_slow
        breakout_confirmed = current.close > breakout_level * (1.0 + breakout_buffer_pct)
        volume_confirmed = volume_ratio >= volume_surge_ratio
        momentum_confirmed = momentum_pct >= min_momentum_pct
        close_strength_confirmed = close_strength >= min_close_strength
        confluence_score = sum(
            (
                int(regime_entry_allowed),
                int(trend_alignment),
                int(breakout_confirmed),
                int(volume_confirmed),
                int(momentum_confirmed and close_strength_confirmed),
            )
        )
        signal_confidence = min(
            1.0,
            (regime_confidence * 0.35)
            + (0.15 if trend_alignment else 0.0)
            + (self._scaled_score(max((current.close / max(breakout_level, 1e-9)) - 1.0, 0.0), breakout_buffer_pct) * 0.2)
            + (self._scaled_score(max(volume_ratio - 1.0, 0.0), max(volume_surge_ratio - 1.0, 0.05)) * 0.15)
            + (self._scaled_score(max(momentum_pct, 0.0), max(min_momentum_pct, 0.001)) * 0.15),
        )

        matched_conditions: list[str] = []
        failed_conditions: list[str] = []
        self._append_condition(matched_conditions, failed_conditions, regime_entry_allowed, f"composer.{self.composer_id}.regime.entry_allowed")
        self._append_condition(matched_conditions, failed_conditions, trend_alignment, f"composer.{self.composer_id}.trend_alignment")
        self._append_condition(matched_conditions, failed_conditions, breakout_confirmed, f"composer.{self.composer_id}.breakout.confirmed")
        self._append_condition(matched_conditions, failed_conditions, volume_confirmed, f"composer.{self.composer_id}.volume.confirmed")
        self._append_condition(
            matched_conditions,
            failed_conditions,
            momentum_confirmed and close_strength_confirmed,
            f"composer.{self.composer_id}.momentum.confirmed",
        )

        facts = (
            ExplainItem(label=f"composer.{self.composer_id}.regime_state", value=regime_state),
            ExplainItem(label=f"composer.{self.composer_id}.regime_label", value=regime_label),
            ExplainItem(label=f"composer.{self.composer_id}.regime_confidence", value=regime_confidence),
            ExplainItem(label=f"composer.{self.composer_id}.regime_entry_allowed", value=regime_entry_allowed),
            ExplainItem(label=f"composer.{self.composer_id}.atr_pct", value=atr_pct),
            ExplainItem(label=f"composer.{self.composer_id}.ema_fast", value=ema_fast),
            ExplainItem(label=f"composer.{self.composer_id}.ema_slow", value=ema_slow),
            ExplainItem(label=f"composer.{self.composer_id}.breakout_level", value=breakout_level),
            ExplainItem(label=f"composer.{self.composer_id}.support_price", value=support_price),
            ExplainItem(label=f"composer.{self.composer_id}.fallback_floor", value=fallback_floor),
            ExplainItem(label=f"composer.{self.composer_id}.momentum_pct", value=momentum_pct),
            ExplainItem(label=f"composer.{self.composer_id}.volume_ratio", value=volume_ratio),
            ExplainItem(label=f"composer.{self.composer_id}.close_strength", value=close_strength),
            ExplainItem(label=f"composer.{self.composer_id}.signal_confidence", value=signal_confidence),
            ExplainItem(label=f"composer.{self.composer_id}.confluence_score", value=confluence_score),
        )
        structures = tuple(item for item in (trend, swing) if item is not None)

        breakout_failed = current.close < breakout_level * (1.0 - exit_breakdown_pct)
        ema_lost = current.close < ema_fast and ema_fast < ema_slow
        regime_lost = regime_state in {"trend_down", "range"}
        exit_reason_codes: list[str] = []
        if regime_state == "trend_down":
            exit_reason_codes.append("PLUGIN_ZENITH_HAZEL_REGIME_DOWN_EXIT")
        if breakout_failed:
            exit_reason_codes.append("PLUGIN_ZENITH_HAZEL_BREAKOUT_FAILURE_EXIT")
        if ema_lost:
            exit_reason_codes.append("PLUGIN_ZENITH_HAZEL_EMA_LOSS_EXIT")
        if regime_state == "high_volatility" and not allow_high_volatility_breakout:
            exit_reason_codes.append("PLUGIN_ZENITH_HAZEL_VOLATILITY_EXIT")

        confluence = SetupConfluence(
            score=confluence_score,
            max_score=5,
            matched_conditions=tuple(matched_conditions),
            failed_conditions=tuple(failed_conditions),
            facts=(ExplainItem(label=f"composer.{self.composer_id}.signal_confidence", value=signal_confidence),),
            reason_codes=("PLUGIN_ZENITH_HAZEL_ENTRY",) if confluence_score >= min_signal_score else ("PLUGIN_HOLD",),
        )

        stop_loss_price = support_price * (1.0 - stop_buffer_pct)
        if stop_loss_price >= current.close:
            stop_loss_price = fallback_floor * (1.0 - stop_buffer_pct)
        take_profit_price = current.close + max(current.close - stop_loss_price, 0.0) * rr_target
        preferred_entry_zone = (min(ema_fast, breakout_level), max(ema_fast, breakout_level))
        risk = RiskEnvelope(
            invalidation_price=stop_loss_price,
            stop_loss_price=stop_loss_price,
            take_profit_prices=(take_profit_price,),
            trailing_activation_price=None,
            max_holding_bars=time_exit_bars,
        )
        entry_setup = EntrySetup(
            setup_id=f"zenith_entry:{context.symbol}:{timeframe}:{current.candle_start.isoformat()}",
            symbol=context.symbol,
            timeframe=timeframe,
            direction="long",
            setup_type="zenith_regime_momentum_long",
            valid=False,
            confidence=signal_confidence,
            trigger_price=current.close,
            preferred_entry_zone=preferred_entry_zone,
            invalidation_price=stop_loss_price,
            confluence=confluence,
            risk=risk,
            structures=structures,
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_ZENITH_HAZEL_ENTRY",),
        )

        exit_setup: ExitSetup | None = None
        if exit_reason_codes and (regime_lost or breakout_failed or ema_lost):
            exit_setup = ExitSetup(
                setup_id=f"zenith_exit:{context.symbol}:{timeframe}:{current.candle_start.isoformat()}",
                symbol=context.symbol,
                timeframe=timeframe,
                exit_type="regime_momentum_invalidation",
                valid=True,
                priority=1,
                trigger_price=current.close,
                invalidation_price=breakout_level,
                structures=structures,
                facts=facts,
                parameters=parameters,
                reason_codes=tuple(exit_reason_codes),
            )

        entry_valid = (
            regime_entry_allowed
            and trend_alignment
            and breakout_confirmed
            and volume_confirmed
            and momentum_confirmed
            and close_strength_confirmed
            and confluence_score >= min_signal_score
            and signal_confidence >= min_signal_confidence
            and stop_loss_price < current.close
        )
        entry_setup.valid = entry_valid

        if exit_setup is not None and not entry_valid:
            return StrategyDecisionDraft(
                action="EXIT",
                confidence=min(1.0, max(signal_confidence, 0.6)),
                entry_setup=entry_setup,
                exit_setup=exit_setup,
                matched_conditions=tuple(matched_conditions),
                failed_conditions=tuple(failed_conditions),
                facts=facts,
                parameters=parameters,
                reason_codes=tuple(exit_reason_codes),
            )

        if entry_valid:
            return StrategyDecisionDraft(
                action="ENTER",
                confidence=signal_confidence,
                entry_setup=entry_setup,
                exit_setup=None,
                matched_conditions=tuple(matched_conditions),
                failed_conditions=tuple(failed_conditions),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_ZENITH_HAZEL_ENTRY",),
            )

        return StrategyDecisionDraft(
            action="HOLD",
            confidence=signal_confidence,
            entry_setup=entry_setup,
            exit_setup=exit_setup,
            matched_conditions=tuple(matched_conditions),
            failed_conditions=tuple(failed_conditions),
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_HOLD",),
        )

    def _append_condition(
        self,
        matched_conditions: list[str],
        failed_conditions: list[str],
        matched: bool,
        condition: str,
    ) -> None:
        if matched:
            matched_conditions.append(condition)
            return
        failed_conditions.append(condition)

    def _classify_regime(
        self,
        *,
        trend: TrendContext,
        swing: TrendContext,
        atr_pct: float,
        min_regime_confidence: float,
        high_volatility_atr_pct: float,
    ) -> tuple[str, str, float]:
        trend_confidence = max(trend.confidence or 0.0, 0.0)
        swing_confidence = max(swing.confidence or 0.0, 0.0)
        combined_confidence = min(1.0, (trend_confidence * 0.45) + (swing_confidence * 0.55))

        bullish_confidence = max(combined_confidence, trend_confidence)
        bearish_confidence = max(combined_confidence, trend_confidence)
        if trend.trend_state == "trend_up" and swing.trend_state != "trend_down" and bullish_confidence >= min_regime_confidence:
            return "trend_up", "TRENDING_UP", bullish_confidence
        if trend.trend_state == "trend_down" and swing.trend_state != "trend_up" and bearish_confidence >= min_regime_confidence:
            return "trend_down", "TRENDING_DOWN", bearish_confidence
        if atr_pct >= high_volatility_atr_pct:
            return "high_volatility", "HIGH_VOLATILITY", min(1.0, max(combined_confidence, atr_pct / max(high_volatility_atr_pct, 1e-9)))
        return "range", "RANGING", combined_confidence

    def _ema(self, values: list[float], period: int) -> float:
        if not values:
            return 0.0
        alpha = 2.0 / (period + 1.0)
        ema = values[0]
        for value in values[1:]:
            ema = (value * alpha) + (ema * (1.0 - alpha))
        return ema

    def _scaled_score(self, value: float, threshold: float) -> float:
        if threshold <= 0:
            return 1.0 if value > 0 else 0.0
        return min(1.0, max(value / threshold, 0.0))
