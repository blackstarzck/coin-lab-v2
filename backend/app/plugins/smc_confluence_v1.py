from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.entities.market import CandleState, MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin


@dataclass(frozen=True, slots=True)
class _TrendContext:
    bullish: bool
    support: float
    resistance: float
    average_close: float
    start_close: float
    latest_close: float


@dataclass(frozen=True, slots=True)
class _ZoneSignal:
    kind: str
    lower: float
    upper: float
    invalidation: float
    retested: bool
    formed_at: str


class SmcConfluenceV1Plugin(StrategyPlugin):
    plugin_id = "smc_confluence_v1"
    plugin_version = "1.0.0"

    def validate(self, config: dict[str, object]) -> None:
        timeframe = config.get("timeframe", "5m")
        trend_lookback = config.get("trend_lookback", 12)
        order_block_lookback = config.get("order_block_lookback", 8)
        displacement_min_body_ratio = config.get("displacement_min_body_ratio", 0.55)
        displacement_min_pct = config.get("displacement_min_pct", 0.003)
        fvg_gap_pct = config.get("fvg_gap_pct", 0.001)
        zone_retest_tolerance_pct = config.get("zone_retest_tolerance_pct", 0.0015)
        exit_zone_break_pct = config.get("exit_zone_break_pct", 0.002)
        min_confluence_score = config.get("min_confluence_score", 3)
        require_order_block = config.get("require_order_block", False)
        require_fvg = config.get("require_fvg", False)
        require_confirmation = config.get("require_confirmation", True)

        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("timeframe must be a non-empty string")
        if not isinstance(trend_lookback, int) or trend_lookback < 6:
            raise ValueError("trend_lookback must be an integer greater than or equal to 6")
        if not isinstance(order_block_lookback, int) or order_block_lookback < 4:
            raise ValueError("order_block_lookback must be an integer greater than or equal to 4")
        if not isinstance(displacement_min_body_ratio, (int, float)) or not 0.0 < float(displacement_min_body_ratio) <= 1.0:
            raise ValueError("displacement_min_body_ratio must be a number between 0 and 1")
        if not isinstance(displacement_min_pct, (int, float)) or float(displacement_min_pct) < 0.0:
            raise ValueError("displacement_min_pct must be a non-negative number")
        if not isinstance(fvg_gap_pct, (int, float)) or float(fvg_gap_pct) < 0.0:
            raise ValueError("fvg_gap_pct must be a non-negative number")
        if not isinstance(zone_retest_tolerance_pct, (int, float)) or float(zone_retest_tolerance_pct) < 0.0:
            raise ValueError("zone_retest_tolerance_pct must be a non-negative number")
        if not isinstance(exit_zone_break_pct, (int, float)) or float(exit_zone_break_pct) < 0.0:
            raise ValueError("exit_zone_break_pct must be a non-negative number")
        if not isinstance(min_confluence_score, int) or not 1 <= min_confluence_score <= 4:
            raise ValueError("min_confluence_score must be an integer between 1 and 4")
        if not isinstance(require_order_block, bool):
            raise ValueError("require_order_block must be a boolean")
        if not isinstance(require_fvg, bool):
            raise ValueError("require_fvg must be a boolean")
        if not isinstance(require_confirmation, bool):
            raise ValueError("require_confirmation must be a boolean")

    def evaluate(self, snapshot: Any, config: dict[str, object] | None = None) -> StrategyDecision:
        if not isinstance(snapshot, MarketSnapshot):
            return StrategyDecision(action=PluginAction.HOLD, reason_codes=["PLUGIN_SNAPSHOT_INVALID"])

        plugin_config = config or {}
        self.validate(plugin_config)

        timeframe = str(plugin_config.get("timeframe", "5m"))
        trend_lookback = int(plugin_config.get("trend_lookback", 12))
        order_block_lookback = int(plugin_config.get("order_block_lookback", 8))
        displacement_min_body_ratio = float(plugin_config.get("displacement_min_body_ratio", 0.55))
        displacement_min_pct = float(plugin_config.get("displacement_min_pct", 0.003))
        fvg_gap_pct = float(plugin_config.get("fvg_gap_pct", 0.001))
        zone_retest_tolerance_pct = float(plugin_config.get("zone_retest_tolerance_pct", 0.0015))
        exit_zone_break_pct = float(plugin_config.get("exit_zone_break_pct", 0.002))
        min_confluence_score = int(plugin_config.get("min_confluence_score", 3))
        require_order_block = bool(plugin_config.get("require_order_block", False))
        require_fvg = bool(plugin_config.get("require_fvg", False))
        require_confirmation = bool(plugin_config.get("require_confirmation", True))

        candles = self._candles(snapshot, timeframe)
        signal_price = snapshot.latest_price if snapshot.latest_price is not None else (candles[-1].close if candles else None)
        minimum_history = max(trend_lookback, order_block_lookback + 3, 6)
        if len(candles) < minimum_history:
            return StrategyDecision(
                action=PluginAction.HOLD,
                signal_price=signal_price,
                reason_codes=["PLUGIN_NOT_READY"],
                failed_conditions=[f"plugin.smc_confluence_v1.{timeframe}.history_ready"],
                parameters=self._parameters(
                    timeframe=timeframe,
                    trend_lookback=trend_lookback,
                    order_block_lookback=order_block_lookback,
                    displacement_min_body_ratio=displacement_min_body_ratio,
                    displacement_min_pct=displacement_min_pct,
                    fvg_gap_pct=fvg_gap_pct,
                    zone_retest_tolerance_pct=zone_retest_tolerance_pct,
                    exit_zone_break_pct=exit_zone_break_pct,
                    min_confluence_score=min_confluence_score,
                    require_order_block=require_order_block,
                    require_fvg=require_fvg,
                    require_confirmation=require_confirmation,
                ),
            )

        current = candles[-1]
        if not current.is_closed and timeframe not in snapshot.closed_timeframes and snapshot.source_event_type is not None:
            return StrategyDecision(
                action=PluginAction.HOLD,
                signal_price=signal_price,
                reason_codes=["PLUGIN_WAIT_CANDLE_CLOSE"],
                failed_conditions=[f"plugin.smc_confluence_v1.{timeframe}.candle_closed"],
                parameters=self._parameters(
                    timeframe=timeframe,
                    trend_lookback=trend_lookback,
                    order_block_lookback=order_block_lookback,
                    displacement_min_body_ratio=displacement_min_body_ratio,
                    displacement_min_pct=displacement_min_pct,
                    fvg_gap_pct=fvg_gap_pct,
                    zone_retest_tolerance_pct=zone_retest_tolerance_pct,
                    exit_zone_break_pct=exit_zone_break_pct,
                    min_confluence_score=min_confluence_score,
                    require_order_block=require_order_block,
                    require_fvg=require_fvg,
                    require_confirmation=require_confirmation,
                ),
            )

        trend = self._trend_context(candles, trend_lookback)
        order_block = self._detect_bullish_order_block(
            candles=candles,
            lookback=order_block_lookback,
            body_ratio_threshold=displacement_min_body_ratio,
            body_pct_threshold=displacement_min_pct,
            retest_tolerance_pct=zone_retest_tolerance_pct,
            invalidation_buffer_pct=exit_zone_break_pct,
        )
        fair_value_gap = self._detect_bullish_fvg(
            candles=candles,
            gap_threshold_pct=fvg_gap_pct,
            body_ratio_threshold=displacement_min_body_ratio,
            body_pct_threshold=displacement_min_pct,
            retest_tolerance_pct=zone_retest_tolerance_pct,
            invalidation_buffer_pct=exit_zone_break_pct,
        )
        confirmation_ok = self._is_confirmation_candle(current)
        order_block_retested = order_block is not None and order_block.retested
        fvg_retested = fair_value_gap is not None and fair_value_gap.retested
        confluence_score = int(trend.bullish) + int(order_block_retested) + int(fvg_retested) + int(confirmation_ok)

        matched_conditions: list[str] = []
        failed_conditions: list[str] = []
        self._append_condition(matched_conditions, failed_conditions, trend.bullish, "plugin.smc_confluence_v1.trend_context.bullish")
        self._append_condition(matched_conditions, failed_conditions, order_block_retested, "plugin.smc_confluence_v1.order_block.retested")
        self._append_condition(matched_conditions, failed_conditions, fvg_retested, "plugin.smc_confluence_v1.fvg.retested")
        self._append_condition(matched_conditions, failed_conditions, confirmation_ok, "plugin.smc_confluence_v1.confirmation_candle")

        facts = self._facts(
            timeframe=timeframe,
            current=current,
            trend=trend,
            order_block=order_block,
            fair_value_gap=fair_value_gap,
            confirmation_ok=confirmation_ok,
            confluence_score=confluence_score,
        )
        parameters = self._parameters(
            timeframe=timeframe,
            trend_lookback=trend_lookback,
            order_block_lookback=order_block_lookback,
            displacement_min_body_ratio=displacement_min_body_ratio,
            displacement_min_pct=displacement_min_pct,
            fvg_gap_pct=fvg_gap_pct,
            zone_retest_tolerance_pct=zone_retest_tolerance_pct,
            exit_zone_break_pct=exit_zone_break_pct,
            min_confluence_score=min_confluence_score,
            require_order_block=require_order_block,
            require_fvg=require_fvg,
            require_confirmation=require_confirmation,
        )

        order_block_broken = order_block is not None and current.close < order_block.invalidation
        fvg_broken = fair_value_gap is not None and current.close < fair_value_gap.invalidation
        trend_broken = current.close < trend.support and current.close < trend.average_close
        exit_reason_codes: list[str] = []
        if order_block_broken:
            exit_reason_codes.append("PLUGIN_SMC_EXIT_ORDER_BLOCK_BROKEN")
        if fvg_broken:
            exit_reason_codes.append("PLUGIN_SMC_EXIT_FVG_BROKEN")
        if trend_broken:
            exit_reason_codes.append("PLUGIN_SMC_EXIT_TREND_INVALIDATION")
        if exit_reason_codes:
            return StrategyDecision(
                action=PluginAction.EXIT,
                confidence=min(1.0, 0.5 + 0.15 * len(exit_reason_codes)),
                signal_price=signal_price,
                reason_codes=exit_reason_codes,
                matched_conditions=matched_conditions + [f"plugin.smc_confluence_v1.{code.lower()}" for code in exit_reason_codes],
                failed_conditions=failed_conditions,
                facts=facts,
                parameters=parameters,
            )

        zones_ready = order_block_retested or fvg_retested
        required_checks_met = (
            (not require_order_block or order_block_retested)
            and (not require_fvg or fvg_retested)
            and (not require_confirmation or confirmation_ok)
            and trend.bullish
        )
        if zones_ready and required_checks_met and confluence_score >= min_confluence_score:
            return StrategyDecision(
                action=PluginAction.ENTER,
                confidence=min(1.0, confluence_score / 4.0),
                signal_price=signal_price,
                reason_codes=["PLUGIN_SMC_CONFLUENCE_ENTRY"],
                matched_conditions=matched_conditions,
                failed_conditions=failed_conditions,
                facts=facts,
                parameters=parameters,
            )

        return StrategyDecision(
            action=PluginAction.HOLD,
            confidence=max(0.0, confluence_score / 4.0),
            signal_price=signal_price,
            reason_codes=["PLUGIN_HOLD"],
            matched_conditions=matched_conditions,
            failed_conditions=failed_conditions,
            facts=facts,
            parameters=parameters,
        )

    def explain(self, snapshot: Any, config: dict[str, object] | None = None) -> dict[str, object]:
        decision = self.evaluate(snapshot, config)
        return {
            "decision": decision.action.value,
            "reason_codes": decision.reason_codes,
            "facts": decision.facts,
            "parameters": decision.parameters,
            "matched_conditions": decision.matched_conditions,
            "failed_conditions": decision.failed_conditions,
        }

    def _candles(self, snapshot: MarketSnapshot, timeframe: str) -> list[CandleState]:
        history = list(snapshot.candle_history.get(timeframe, ()))
        current = snapshot.candles.get(timeframe)
        if current is None:
            return history
        if history and history[-1].candle_start == current.candle_start:
            history[-1] = current
        else:
            history.append(current)
        return history

    def _trend_context(self, candles: list[CandleState], lookback: int) -> _TrendContext:
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
        return _TrendContext(
            bullish=bullish,
            support=late_support,
            resistance=late_resistance,
            average_close=average_close,
            start_close=start_close,
            latest_close=latest_close,
        )

    def _detect_bullish_fvg(
        self,
        *,
        candles: list[CandleState],
        gap_threshold_pct: float,
        body_ratio_threshold: float,
        body_pct_threshold: float,
        retest_tolerance_pct: float,
        invalidation_buffer_pct: float,
    ) -> _ZoneSignal | None:
        if len(candles) < 4:
            return None

        current = candles[-1]
        for index in range(len(candles) - 4, -1, -1):
            left = candles[index]
            middle = candles[index + 1]
            right = candles[index + 2]
            if not self._is_strong_bullish_candle(middle, body_ratio_threshold, body_pct_threshold):
                continue
            if right.low <= left.high:
                continue
            gap_pct = (right.low - left.high) / max(left.high, 1e-9)
            if gap_pct < gap_threshold_pct:
                continue
            zone_low = left.high
            zone_high = right.low
            if any(candidate.close < zone_low for candidate in candles[index + 3:-1]):
                continue
            retested = current.low <= zone_high * (1.0 + retest_tolerance_pct) and current.high >= zone_low
            return _ZoneSignal(
                kind="fvg",
                lower=zone_low,
                upper=zone_high,
                invalidation=zone_low * (1.0 - invalidation_buffer_pct),
                retested=retested,
                formed_at=right.candle_start.isoformat(),
            )
        return None

    def _detect_bullish_order_block(
        self,
        *,
        candles: list[CandleState],
        lookback: int,
        body_ratio_threshold: float,
        body_pct_threshold: float,
        retest_tolerance_pct: float,
        invalidation_buffer_pct: float,
    ) -> _ZoneSignal | None:
        if len(candles) < 5:
            return None

        current = candles[-1]
        start_index = max(0, len(candles) - 1 - lookback - 3)
        for index in range(len(candles) - 4, start_index - 1, -1):
            candidate = candles[index]
            if candidate.close >= candidate.open:
                continue
            impulse = candles[index + 1]
            follow = candles[index + 2]
            if not self._is_strong_bullish_candle(impulse, body_ratio_threshold, body_pct_threshold):
                continue
            prior_window = candles[max(0, index - 3):index + 1]
            prior_high = max(candle.high for candle in prior_window)
            structure_break = max(impulse.close, impulse.high, follow.close, follow.high) > prior_high and impulse.close > candidate.high
            if not structure_break:
                continue
            zone_low = candidate.low
            zone_high = candidate.open
            if any(next_candle.close < zone_low for next_candle in candles[index + 2:-1]):
                continue
            retested = current.low <= zone_high * (1.0 + retest_tolerance_pct) and current.high >= zone_low
            return _ZoneSignal(
                kind="order_block",
                lower=zone_low,
                upper=zone_high,
                invalidation=zone_low * (1.0 - invalidation_buffer_pct),
                retested=retested,
                formed_at=candidate.candle_start.isoformat(),
            )
        return None

    def _is_confirmation_candle(self, candle: CandleState) -> bool:
        if candle.close <= candle.open:
            return False
        candle_range = max(candle.high - candle.low, 0.0)
        if candle_range <= 0:
            return False
        close_position = (candle.close - candle.low) / candle_range
        body_ratio = abs(candle.close - candle.open) / candle_range
        return close_position >= 0.6 and body_ratio >= 0.45

    def _is_strong_bullish_candle(self, candle: CandleState, body_ratio_threshold: float, body_pct_threshold: float) -> bool:
        if candle.close <= candle.open:
            return False
        candle_range = max(candle.high - candle.low, 0.0)
        if candle_range <= 0:
            return False
        body_ratio = abs(candle.close - candle.open) / candle_range
        body_pct = abs(candle.close - candle.open) / max(candle.open, 1e-9)
        return body_ratio >= body_ratio_threshold and body_pct >= body_pct_threshold

    def _facts(
        self,
        *,
        timeframe: str,
        current: CandleState,
        trend: _TrendContext,
        order_block: _ZoneSignal | None,
        fair_value_gap: _ZoneSignal | None,
        confirmation_ok: bool,
        confluence_score: int,
    ) -> list[dict[str, float | int | bool | str]]:
        facts: list[dict[str, float | int | bool | str]] = [
            {"label": f"{timeframe}.close", "value": current.close},
            {"label": f"{timeframe}.low", "value": current.low},
            {"label": f"{timeframe}.high", "value": current.high},
            {"label": "plugin.smc_confluence_v1.trend_bullish", "value": trend.bullish},
            {"label": "plugin.smc_confluence_v1.trend_support", "value": trend.support},
            {"label": "plugin.smc_confluence_v1.trend_resistance", "value": trend.resistance},
            {"label": "plugin.smc_confluence_v1.average_close", "value": trend.average_close},
            {"label": "plugin.smc_confluence_v1.confirmation_ok", "value": confirmation_ok},
            {"label": "plugin.smc_confluence_v1.confluence_score", "value": confluence_score},
        ]
        if order_block is not None:
            facts.extend([
                {"label": "plugin.smc_confluence_v1.order_block.lower", "value": order_block.lower},
                {"label": "plugin.smc_confluence_v1.order_block.upper", "value": order_block.upper},
                {"label": "plugin.smc_confluence_v1.order_block.invalidation", "value": order_block.invalidation},
                {"label": "plugin.smc_confluence_v1.order_block.retested", "value": order_block.retested},
                {"label": "plugin.smc_confluence_v1.order_block.formed_at", "value": order_block.formed_at},
            ])
        if fair_value_gap is not None:
            facts.extend([
                {"label": "plugin.smc_confluence_v1.fvg.lower", "value": fair_value_gap.lower},
                {"label": "plugin.smc_confluence_v1.fvg.upper", "value": fair_value_gap.upper},
                {"label": "plugin.smc_confluence_v1.fvg.invalidation", "value": fair_value_gap.invalidation},
                {"label": "plugin.smc_confluence_v1.fvg.retested", "value": fair_value_gap.retested},
                {"label": "plugin.smc_confluence_v1.fvg.formed_at", "value": fair_value_gap.formed_at},
            ])
        return facts

    def _parameters(
        self,
        *,
        timeframe: str,
        trend_lookback: int,
        order_block_lookback: int,
        displacement_min_body_ratio: float,
        displacement_min_pct: float,
        fvg_gap_pct: float,
        zone_retest_tolerance_pct: float,
        exit_zone_break_pct: float,
        min_confluence_score: int,
        require_order_block: bool,
        require_fvg: bool,
        require_confirmation: bool,
    ) -> list[dict[str, float | int | bool | str]]:
        return [
            {"label": "plugin.smc_confluence_v1.timeframe", "value": timeframe},
            {"label": "plugin.smc_confluence_v1.trend_lookback", "value": trend_lookback},
            {"label": "plugin.smc_confluence_v1.order_block_lookback", "value": order_block_lookback},
            {"label": "plugin.smc_confluence_v1.displacement_min_body_ratio", "value": displacement_min_body_ratio},
            {"label": "plugin.smc_confluence_v1.displacement_min_pct", "value": displacement_min_pct},
            {"label": "plugin.smc_confluence_v1.fvg_gap_pct", "value": fvg_gap_pct},
            {"label": "plugin.smc_confluence_v1.zone_retest_tolerance_pct", "value": zone_retest_tolerance_pct},
            {"label": "plugin.smc_confluence_v1.exit_zone_break_pct", "value": exit_zone_break_pct},
            {"label": "plugin.smc_confluence_v1.min_confluence_score", "value": min_confluence_score},
            {"label": "plugin.smc_confluence_v1.require_order_block", "value": require_order_block},
            {"label": "plugin.smc_confluence_v1.require_fvg", "value": require_fvg},
            {"label": "plugin.smc_confluence_v1.require_confirmation", "value": require_confirmation},
        ]

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
