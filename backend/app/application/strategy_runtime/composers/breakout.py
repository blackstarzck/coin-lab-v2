from __future__ import annotations

from app.application.strategy_runtime.detectors import resolve_candles
from app.domain.strategy_runtime import (
    EntrySetup,
    ExplainItem,
    ExitSetup,
    RiskEnvelope,
    SetupConfluence,
    StrategyDecisionDraft,
)

from .base import ComposerContext, StrategyComposer


class BreakoutComposer(StrategyComposer):
    composer_id = "breakout_v1"

    def validate(self, config: dict[str, object]) -> None:
        timeframe = config.get("timeframe", "5m")
        lookback = config.get("lookback", 20)
        breakout_pct = config.get("breakout_pct", 0.0)
        exit_breakdown_pct = config.get("exit_breakdown_pct", 0.0)

        if not isinstance(timeframe, str) or not timeframe.strip():
            raise ValueError("timeframe must be a non-empty string")
        if not isinstance(lookback, int) or lookback <= 1:
            raise ValueError("lookback must be an integer greater than 1")
        if not isinstance(breakout_pct, (int, float)) or float(breakout_pct) < 0:
            raise ValueError("breakout_pct must be a non-negative number")
        if not isinstance(exit_breakdown_pct, (int, float)) or float(exit_breakdown_pct) < 0:
            raise ValueError("exit_breakdown_pct must be a non-negative number")

    def compose(self, context: ComposerContext) -> StrategyDecisionDraft:
        self.validate(context.config)
        timeframe = str(context.config.get("timeframe", context.timeframe))
        lookback = int(context.config.get("lookback", 20))
        breakout_pct = float(context.config.get("breakout_pct", 0.0))
        exit_breakdown_pct = float(context.config.get("exit_breakdown_pct", 0.0))

        candles = resolve_candles(context.snapshot, timeframe)
        parameters = (
            ExplainItem(label="composer.breakout.timeframe", value=timeframe),
            ExplainItem(label="composer.breakout.lookback", value=lookback),
            ExplainItem(label="composer.breakout.breakout_pct", value=breakout_pct),
            ExplainItem(label="composer.breakout.exit_breakdown_pct", value=exit_breakdown_pct),
        )
        if len(candles) < lookback + 1:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=("composer.breakout.history_ready",),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        current = candles[-1]
        recent = candles[-lookback - 1:-1]
        highest_close = max(candle.close for candle in recent)
        lowest_close = min(candle.close for candle in recent)
        entry_trigger = highest_close * (1.0 + breakout_pct)
        exit_trigger = lowest_close * (1.0 - exit_breakdown_pct)
        facts = (
            ExplainItem(label=f"{timeframe}.close", value=current.close),
            ExplainItem(label="composer.breakout.highest_close", value=highest_close),
            ExplainItem(label="composer.breakout.lowest_close", value=lowest_close),
            ExplainItem(label="composer.breakout.entry_trigger", value=entry_trigger),
            ExplainItem(label="composer.breakout.exit_trigger", value=exit_trigger),
        )

        if current.close <= exit_trigger:
            exit_setup = ExitSetup(
                setup_id=f"breakout_exit:{context.symbol}:{timeframe}:{current.candle_start.isoformat()}",
                symbol=context.symbol,
                timeframe=timeframe,
                exit_type="breakdown_exit",
                valid=True,
                priority=1,
                trigger_price=exit_trigger,
                invalidation_price=None,
                structures=(),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_BREAKDOWN_EXIT",),
            )
            return StrategyDecisionDraft(
                action="EXIT",
                confidence=1.0,
                entry_setup=None,
                exit_setup=exit_setup,
                matched_conditions=("composer.breakout.breakdown_exit",),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_BREAKDOWN_EXIT",),
            )

        if current.close >= entry_trigger:
            confluence = SetupConfluence(
                score=1,
                max_score=1,
                matched_conditions=("composer.breakout.breakout_entry",),
                failed_conditions=(),
            )
            risk = RiskEnvelope(
                invalidation_price=exit_trigger,
                stop_loss_price=exit_trigger,
                take_profit_prices=(),
                trailing_activation_price=None,
                max_holding_bars=None,
            )
            entry_setup = EntrySetup(
                setup_id=f"breakout_entry:{context.symbol}:{timeframe}:{current.candle_start.isoformat()}",
                symbol=context.symbol,
                timeframe=timeframe,
                direction="long",
                setup_type="breakout_continuation_long",
                valid=True,
                confidence=1.0,
                trigger_price=entry_trigger,
                preferred_entry_zone=None,
                invalidation_price=exit_trigger,
                confluence=confluence,
                risk=risk,
                structures=(),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_BREAKOUT_ENTRY",),
            )
            return StrategyDecisionDraft(
                action="ENTER",
                confidence=1.0,
                entry_setup=entry_setup,
                exit_setup=None,
                matched_conditions=("composer.breakout.breakout_entry",),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_BREAKOUT_ENTRY",),
            )

        return StrategyDecisionDraft(
            action="HOLD",
            confidence=0.0,
            entry_setup=None,
            exit_setup=None,
            failed_conditions=("composer.breakout.breakout_entry", "composer.breakout.breakdown_exit"),
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_HOLD",),
        )
