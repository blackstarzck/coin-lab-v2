from __future__ import annotations

from typing import Any

from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin


class BreakoutV1Plugin(StrategyPlugin):
    plugin_id = "breakout_v1"
    plugin_version = "1.0.0"

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

    def evaluate(self, snapshot: Any, config: dict[str, object] | None = None) -> StrategyDecision:
        if not isinstance(snapshot, MarketSnapshot):
            return StrategyDecision(action=PluginAction.HOLD, reason_codes=["PLUGIN_SNAPSHOT_INVALID"])

        plugin_config = config or {}
        self.validate(plugin_config)

        timeframe = str(plugin_config.get("timeframe", "5m"))
        lookback = int(plugin_config.get("lookback", 20))
        breakout_pct = float(plugin_config.get("breakout_pct", 0.0))
        exit_breakdown_pct = float(plugin_config.get("exit_breakdown_pct", 0.0))

        current_candle = snapshot.candles.get(timeframe)
        history = list(snapshot.candle_history.get(timeframe, ()))
        if current_candle is None or len(history) < lookback:
            return StrategyDecision(
                action=PluginAction.HOLD,
                signal_price=snapshot.latest_price,
                reason_codes=["PLUGIN_NOT_READY"],
                failed_conditions=[f"plugin.breakout_v1.{timeframe}.history_ready"],
                parameters=self._parameters(timeframe, lookback, breakout_pct, exit_breakdown_pct),
            )

        recent = history[-lookback:]
        highest_close = max(candle.close for candle in recent)
        lowest_close = min(candle.close for candle in recent)
        latest_close = current_candle.close
        entry_trigger = highest_close * (1 + breakout_pct)
        exit_trigger = lowest_close * (1 - exit_breakdown_pct)
        signal_price = snapshot.latest_price if snapshot.latest_price is not None else latest_close

        facts = [
            {"label": f"{timeframe}.close", "value": latest_close},
            {"label": "plugin.breakout_v1.highest_close", "value": highest_close},
            {"label": "plugin.breakout_v1.lowest_close", "value": lowest_close},
            {"label": "plugin.breakout_v1.entry_trigger", "value": entry_trigger},
            {"label": "plugin.breakout_v1.exit_trigger", "value": exit_trigger},
        ]
        parameters = self._parameters(timeframe, lookback, breakout_pct, exit_breakdown_pct)

        if latest_close <= exit_trigger:
            return StrategyDecision(
                action=PluginAction.EXIT,
                confidence=1.0,
                signal_price=signal_price,
                reason_codes=["PLUGIN_BREAKDOWN_EXIT"],
                matched_conditions=[f"{timeframe}.close <= plugin.breakout_v1.exit_trigger"],
                facts=facts,
                parameters=parameters,
            )

        if latest_close >= entry_trigger:
            return StrategyDecision(
                action=PluginAction.ENTER,
                confidence=1.0,
                signal_price=signal_price,
                reason_codes=["PLUGIN_BREAKOUT_ENTRY"],
                matched_conditions=[f"{timeframe}.close >= plugin.breakout_v1.entry_trigger"],
                facts=facts,
                parameters=parameters,
            )

        return StrategyDecision(
            action=PluginAction.HOLD,
            confidence=0.0,
            signal_price=signal_price,
            reason_codes=["PLUGIN_HOLD"],
            failed_conditions=[
                f"{timeframe}.close >= plugin.breakout_v1.entry_trigger",
                f"{timeframe}.close <= plugin.breakout_v1.exit_trigger",
            ],
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

    def _parameters(
        self,
        timeframe: str,
        lookback: int,
        breakout_pct: float,
        exit_breakdown_pct: float,
    ) -> list[dict[str, float | int | str]]:
        return [
            {"label": "plugin.breakout_v1.timeframe", "value": timeframe},
            {"label": "plugin.breakout_v1.lookback", "value": lookback},
            {"label": "plugin.breakout_v1.breakout_pct", "value": breakout_pct},
            {"label": "plugin.breakout_v1.exit_breakdown_pct", "value": exit_breakdown_pct},
        ]
