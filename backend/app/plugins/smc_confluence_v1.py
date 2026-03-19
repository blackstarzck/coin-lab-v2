from __future__ import annotations

from typing import Any

from app.application.strategy_runtime import ComposerContext, SmcConfluenceComposer, draft_to_explain_payload, draft_to_strategy_decision
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin


class SmcConfluenceV1Plugin(StrategyPlugin):
    plugin_id = "smc_confluence_v1"
    plugin_version = "1.0.0"

    def __init__(self) -> None:
        self._composer = SmcConfluenceComposer()

    def validate(self, config: dict[str, object]) -> None:
        self._composer.validate(config)

    def evaluate(self, snapshot: Any, config: dict[str, object] | None = None) -> StrategyDecision:
        if not isinstance(snapshot, MarketSnapshot):
            return StrategyDecision(action=PluginAction.HOLD, reason_codes=["PLUGIN_SNAPSHOT_INVALID"])

        plugin_config = config or {}
        self.validate(plugin_config)
        draft = self._composer.compose(
            ComposerContext(
                snapshot=snapshot,
                symbol=snapshot.symbol,
                timeframe=str(plugin_config.get("timeframe", "5m")),
                config=plugin_config,
            )
        )
        return draft_to_strategy_decision(draft, snapshot)

    def explain(self, snapshot: Any, config: dict[str, object] | None = None) -> dict[str, object]:
        if not isinstance(snapshot, MarketSnapshot):
            return {
                "decision": PluginAction.HOLD.value,
                "reason_codes": ["PLUGIN_SNAPSHOT_INVALID"],
                "facts": [],
                "parameters": [],
                "matched_conditions": [],
                "failed_conditions": [],
            }

        plugin_config = config or {}
        self.validate(plugin_config)
        draft = self._composer.compose(
            ComposerContext(
                snapshot=snapshot,
                symbol=snapshot.symbol,
                timeframe=str(plugin_config.get("timeframe", "5m")),
                config=plugin_config,
            )
        )
        return draft_to_explain_payload(
            snapshot=snapshot,
            draft=draft,
            timeframe=str(plugin_config.get("timeframe", "5m")),
            fallback_decision=PluginAction.HOLD.value,
        )
