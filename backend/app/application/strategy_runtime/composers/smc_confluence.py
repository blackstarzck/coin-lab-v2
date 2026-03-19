from __future__ import annotations

from app.application.strategy_runtime.detectors import (
    DetectorContext,
    FairValueGapDetector,
    OrderBlockDetector,
    RetestDetector,
    StructureBreakDetector,
    TrendContextDetector,
    is_confirmation_candle,
    resolve_candles,
)
from app.domain.strategy_runtime import (
    EntrySetup,
    ExitSetup,
    ExplainItem,
    FairValueGapZone,
    OrderBlockZone,
    RetestEvaluation,
    RiskEnvelope,
    SetupConfluence,
    StrategyDecisionDraft,
    StructureBreak,
    TrendContext,
)

from .base import ComposerContext, StrategyComposer


class SmcConfluenceComposer(StrategyComposer):
    composer_id = "smc_confluence_v1"

    def __init__(self) -> None:
        self._trend_detector = TrendContextDetector()
        self._order_block_detector = OrderBlockDetector()
        self._fvg_detector = FairValueGapDetector()
        self._structure_break_detector = StructureBreakDetector()
        self._retest_detector = RetestDetector()

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

    def compose(self, context: ComposerContext) -> StrategyDecisionDraft:
        self.validate(context.config)

        timeframe = str(context.config.get("timeframe", context.timeframe))
        trend_lookback = int(context.config.get("trend_lookback", 12))
        order_block_lookback = int(context.config.get("order_block_lookback", 8))
        displacement_min_body_ratio = float(context.config.get("displacement_min_body_ratio", 0.55))
        displacement_min_pct = float(context.config.get("displacement_min_pct", 0.003))
        fvg_gap_pct = float(context.config.get("fvg_gap_pct", 0.001))
        zone_retest_tolerance_pct = float(context.config.get("zone_retest_tolerance_pct", 0.0015))
        exit_zone_break_pct = float(context.config.get("exit_zone_break_pct", 0.002))
        min_confluence_score = int(context.config.get("min_confluence_score", 3))
        require_order_block = bool(context.config.get("require_order_block", False))
        require_fvg = bool(context.config.get("require_fvg", False))
        require_confirmation = bool(context.config.get("require_confirmation", True))

        candles = resolve_candles(context.snapshot, timeframe)
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
        minimum_history = max(
            self._trend_detector.required_history({"lookback": trend_lookback}),
            self._order_block_detector.required_history({"lookback": order_block_lookback}),
            self._fvg_detector.required_history({}),
            self._structure_break_detector.required_history({"swing_lookback": max(3, trend_lookback // 2)}),
            6,
        )
        if len(candles) < minimum_history:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(f"composer.smc_confluence_v1.{timeframe}.history_ready",),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        current = candles[-1]
        base_kwargs = {
            "snapshot": context.snapshot,
            "symbol": context.symbol,
            "timeframe": timeframe,
        }
        trend_result = self._trend_detector.evaluate(
            DetectorContext(**base_kwargs, config={"lookback": trend_lookback, "direction": "bullish"})
        )
        if trend_result.primary is None:
            return StrategyDecisionDraft(
                action="HOLD",
                confidence=0.0,
                entry_setup=None,
                exit_setup=None,
                failed_conditions=(f"composer.smc_confluence_v1.{timeframe}.trend_context_ready",),
                parameters=parameters,
                reason_codes=("PLUGIN_NOT_READY",),
            )

        order_block_result = self._order_block_detector.evaluate(
            DetectorContext(
                **base_kwargs,
                config={
                    "lookback": order_block_lookback,
                    "body_ratio_threshold": displacement_min_body_ratio,
                    "body_pct_threshold": displacement_min_pct,
                    "retest_tolerance_pct": zone_retest_tolerance_pct,
                    "invalidation_buffer_pct": exit_zone_break_pct,
                    "direction": "bullish",
                },
            )
        )
        fvg_result = self._fvg_detector.evaluate(
            DetectorContext(
                **base_kwargs,
                config={
                    "gap_threshold_pct": fvg_gap_pct,
                    "body_ratio_threshold": displacement_min_body_ratio,
                    "body_pct_threshold": displacement_min_pct,
                    "retest_tolerance_pct": zone_retest_tolerance_pct,
                    "invalidation_buffer_pct": exit_zone_break_pct,
                    "direction": "bullish",
                },
            )
        )
        structure_break_result = self._structure_break_detector.evaluate(
            DetectorContext(
                **base_kwargs,
                config={
                    "swing_lookback": max(3, min(order_block_lookback, 5)),
                    "break_confirmation": "close",
                    "break_buffer_pct": 0.0,
                    "direction": "bullish",
                },
            )
        )
        order_block_retest = self._evaluate_zone_retest(base_kwargs, order_block_result.primary, zone_retest_tolerance_pct)
        fvg_retest = self._evaluate_zone_retest(base_kwargs, fvg_result.primary, zone_retest_tolerance_pct)

        trend = trend_result.primary
        order_block = order_block_result.primary
        fair_value_gap = fvg_result.primary
        structure_break = structure_break_result.primary
        trend_bullish = trend.trend_state == "trend_up"
        confirmation_ok = is_confirmation_candle(current, direction="bullish")
        order_block_retested = order_block_retest is not None and order_block_retest.accepted
        fvg_retested = fvg_retest is not None and fvg_retest.accepted
        confluence_score = int(trend_bullish) + int(order_block_retested) + int(fvg_retested) + int(confirmation_ok)

        matched_conditions: list[str] = []
        failed_conditions: list[str] = []
        self._append_condition(matched_conditions, failed_conditions, trend_bullish, "composer.smc_confluence_v1.trend_context.bullish")
        self._append_condition(matched_conditions, failed_conditions, order_block_retested, "composer.smc_confluence_v1.order_block.retested")
        self._append_condition(matched_conditions, failed_conditions, fvg_retested, "composer.smc_confluence_v1.fvg.retested")
        self._append_condition(matched_conditions, failed_conditions, confirmation_ok, "composer.smc_confluence_v1.confirmation_candle")

        facts = self._facts(
            timeframe=timeframe,
            current=current,
            trend=trend,
            order_block=order_block,
            order_block_retest=order_block_retest,
            fair_value_gap=fair_value_gap,
            fair_value_gap_retest=fvg_retest,
            structure_break=structure_break,
            confirmation_ok=confirmation_ok,
            confluence_score=confluence_score,
        )
        invalidation_candidates = [
            candidate
            for candidate in (
                order_block.invalidation_price if order_block is not None else None,
                fair_value_gap.invalidation_price if fair_value_gap is not None else None,
                trend.support,
            )
            if candidate is not None
        ]
        invalidation_price = min(invalidation_candidates) if invalidation_candidates else None
        preferred_entry_zone = None
        if order_block is not None and order_block_retested:
            preferred_entry_zone = (order_block.lower, order_block.upper)
        elif fair_value_gap is not None and fvg_retested:
            preferred_entry_zone = (fair_value_gap.lower, fair_value_gap.upper)

        structures = tuple(
            structure
            for structure in (
                trend,
                order_block,
                fair_value_gap,
                structure_break,
                order_block_retest,
                fvg_retest,
            )
            if structure is not None
        )
        confluence = SetupConfluence(
            score=confluence_score,
            max_score=4,
            matched_conditions=tuple(matched_conditions),
            failed_conditions=tuple(failed_conditions),
            facts=(ExplainItem(label="composer.smc_confluence_v1.confluence_score", value=confluence_score),),
            reason_codes=("PLUGIN_SMC_CONFLUENCE_ENTRY",) if confluence_score >= min_confluence_score else ("PLUGIN_HOLD",),
        )
        risk = RiskEnvelope(
            invalidation_price=invalidation_price,
            stop_loss_price=invalidation_price,
            take_profit_prices=(),
            trailing_activation_price=None,
            max_holding_bars=None,
        )
        entry_setup = EntrySetup(
            setup_id=f"smc_entry:{context.symbol}:{timeframe}:{current.candle_start.isoformat()}",
            symbol=context.symbol,
            timeframe=timeframe,
            direction="long",
            setup_type="smc_confluence_long",
            valid=False,
            confidence=min(1.0, confluence_score / 4.0),
            trigger_price=current.close,
            preferred_entry_zone=preferred_entry_zone,
            invalidation_price=invalidation_price,
            confluence=confluence,
            risk=risk,
            structures=structures,
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_SMC_CONFLUENCE_ENTRY",),
        )
        order_block_broken = order_block is not None and current.close < float(order_block.invalidation_price or 0.0)
        fvg_broken = fair_value_gap is not None and current.close < float(fair_value_gap.invalidation_price or 0.0)
        trend_broken = trend.support is not None and trend.average_close is not None and current.close < trend.support and current.close < trend.average_close

        exit_setup: ExitSetup | None = None
        exit_reason_codes: list[str] = []
        if order_block_broken:
            exit_reason_codes.append("PLUGIN_SMC_EXIT_ORDER_BLOCK_BROKEN")
        if fvg_broken:
            exit_reason_codes.append("PLUGIN_SMC_EXIT_FVG_BROKEN")
        if trend_broken:
            exit_reason_codes.append("PLUGIN_SMC_EXIT_TREND_INVALIDATION")
        if exit_reason_codes:
            exit_setup = ExitSetup(
                setup_id=f"smc_exit:{context.symbol}:{timeframe}:{current.candle_start.isoformat()}",
                symbol=context.symbol,
                timeframe=timeframe,
                exit_type="zone_invalidation",
                valid=True,
                priority=1,
                trigger_price=invalidation_price,
                invalidation_price=invalidation_price,
                structures=structures,
                facts=facts,
                parameters=parameters,
                reason_codes=tuple(exit_reason_codes),
            )

        zones_ready = order_block_retested or fvg_retested
        required_checks_met = (
            (not require_order_block or order_block_retested)
            and (not require_fvg or fvg_retested)
            and (not require_confirmation or confirmation_ok)
            and trend_bullish
        )
        entry_valid = zones_ready and required_checks_met and confluence_score >= min_confluence_score
        entry_setup.valid = entry_valid

        if exit_setup is not None:
            return StrategyDecisionDraft(
                action="EXIT",
                confidence=min(1.0, 0.5 + 0.15 * len(exit_reason_codes)),
                entry_setup=entry_setup,
                exit_setup=exit_setup,
                matched_conditions=tuple(matched_conditions + [f"composer.smc_confluence_v1.{code.lower()}" for code in exit_reason_codes]),
                failed_conditions=tuple(failed_conditions),
                facts=facts,
                parameters=parameters,
                reason_codes=tuple(exit_reason_codes),
            )

        if entry_valid:
            return StrategyDecisionDraft(
                action="ENTER",
                confidence=min(1.0, confluence_score / 4.0),
                entry_setup=entry_setup,
                exit_setup=None,
                matched_conditions=tuple(matched_conditions),
                failed_conditions=tuple(failed_conditions),
                facts=facts,
                parameters=parameters,
                reason_codes=("PLUGIN_SMC_CONFLUENCE_ENTRY",),
            )

        return StrategyDecisionDraft(
            action="HOLD",
            confidence=max(0.0, confluence_score / 4.0),
            entry_setup=entry_setup,
            exit_setup=None,
            matched_conditions=tuple(matched_conditions),
            failed_conditions=tuple(failed_conditions),
            facts=facts,
            parameters=parameters,
            reason_codes=("PLUGIN_HOLD",),
        )

    def _evaluate_zone_retest(
        self,
        base_kwargs: dict[str, object],
        target: OrderBlockZone | FairValueGapZone | None,
        tolerance_pct: float,
    ) -> RetestEvaluation | None:
        if target is None:
            return None
        result = self._retest_detector.evaluate(
            DetectorContext(
                **base_kwargs,
                config={
                    "target": target,
                    "zone_kind": target.kind,
                    "tolerance_pct": tolerance_pct,
                    "require_rejection_candle": False,
                },
            )
        )
        return result.primary

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
    ) -> tuple[ExplainItem, ...]:
        return (
            ExplainItem(label="composer.smc_confluence_v1.timeframe", value=timeframe),
            ExplainItem(label="composer.smc_confluence_v1.trend_lookback", value=trend_lookback),
            ExplainItem(label="composer.smc_confluence_v1.order_block_lookback", value=order_block_lookback),
            ExplainItem(label="composer.smc_confluence_v1.displacement_min_body_ratio", value=displacement_min_body_ratio),
            ExplainItem(label="composer.smc_confluence_v1.displacement_min_pct", value=displacement_min_pct),
            ExplainItem(label="composer.smc_confluence_v1.fvg_gap_pct", value=fvg_gap_pct),
            ExplainItem(label="composer.smc_confluence_v1.zone_retest_tolerance_pct", value=zone_retest_tolerance_pct),
            ExplainItem(label="composer.smc_confluence_v1.exit_zone_break_pct", value=exit_zone_break_pct),
            ExplainItem(label="composer.smc_confluence_v1.min_confluence_score", value=min_confluence_score),
            ExplainItem(label="composer.smc_confluence_v1.require_order_block", value=require_order_block),
            ExplainItem(label="composer.smc_confluence_v1.require_fvg", value=require_fvg),
            ExplainItem(label="composer.smc_confluence_v1.require_confirmation", value=require_confirmation),
        )

    def _facts(
        self,
        *,
        timeframe: str,
        current: object,
        trend: TrendContext,
        order_block: OrderBlockZone | None,
        order_block_retest: RetestEvaluation | None,
        fair_value_gap: FairValueGapZone | None,
        fair_value_gap_retest: RetestEvaluation | None,
        structure_break: StructureBreak | None,
        confirmation_ok: bool,
        confluence_score: int,
    ) -> tuple[ExplainItem, ...]:
        candle = current
        facts = [
            ExplainItem(label=f"{timeframe}.close", value=candle.close),
            ExplainItem(label=f"{timeframe}.low", value=candle.low),
            ExplainItem(label=f"{timeframe}.high", value=candle.high),
            ExplainItem(label="composer.smc_confluence_v1.trend_bullish", value=trend.trend_state == "trend_up"),
            ExplainItem(label="composer.smc_confluence_v1.trend_support", value=trend.support),
            ExplainItem(label="composer.smc_confluence_v1.trend_resistance", value=trend.resistance),
            ExplainItem(label="composer.smc_confluence_v1.average_close", value=trend.average_close),
            ExplainItem(label="composer.smc_confluence_v1.confirmation_ok", value=confirmation_ok),
            ExplainItem(label="composer.smc_confluence_v1.confluence_score", value=confluence_score),
        ]
        if order_block is not None:
            facts.extend([
                ExplainItem(label="composer.smc_confluence_v1.order_block.lower", value=order_block.lower),
                ExplainItem(label="composer.smc_confluence_v1.order_block.upper", value=order_block.upper),
                ExplainItem(label="composer.smc_confluence_v1.order_block.invalidation", value=order_block.invalidation_price),
                ExplainItem(label="composer.smc_confluence_v1.order_block.retested", value=order_block_retest.accepted if order_block_retest is not None else False),
            ])
        if fair_value_gap is not None:
            facts.extend([
                ExplainItem(label="composer.smc_confluence_v1.fvg.lower", value=fair_value_gap.lower),
                ExplainItem(label="composer.smc_confluence_v1.fvg.upper", value=fair_value_gap.upper),
                ExplainItem(label="composer.smc_confluence_v1.fvg.invalidation", value=fair_value_gap.invalidation_price),
                ExplainItem(label="composer.smc_confluence_v1.fvg.retested", value=fair_value_gap_retest.accepted if fair_value_gap_retest is not None else False),
            ])
        if structure_break is not None:
            facts.extend([
                ExplainItem(label="composer.smc_confluence_v1.structure_break.type", value=structure_break.break_type),
                ExplainItem(label="composer.smc_confluence_v1.structure_break.price", value=structure_break.break_price),
            ])
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
