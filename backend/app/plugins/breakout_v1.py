from __future__ import annotations

from typing import Any

from app.application.strategy_runtime import BreakoutComposer, ComposerContext, draft_to_explain_payload, draft_to_strategy_decision
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin, StrategyPluginFieldDefinition, StrategyPluginMetadata

from .metadata import timeframe_field


class BreakoutV1Plugin(StrategyPlugin):
    plugin_id = "breakout_v1"
    plugin_version = "1.0.0"

    def __init__(self) -> None:
        self._composer = BreakoutComposer()

    def metadata(self) -> StrategyPluginMetadata:
        return StrategyPluginMetadata(
            plugin_id=self.plugin_id,
            label="Breakout V1",
            version=self.plugin_version,
            description="최근 N개 봉의 최고 종가를 돌파하면 진입하고, 최저 종가를 이탈하면 청산하는 샘플 플러그인입니다.",
            default_config={
                "timeframe": "5m",
                "lookback": 20,
                "breakout_pct": 0.0,
                "exit_breakdown_pct": 0.02,
            },
            fields=(
                timeframe_field("신호를 계산할 캔들 기준입니다."),
                StrategyPluginFieldDefinition(
                    key="lookback",
                    label="룩백 봉 수",
                    kind="integer",
                    helper_text="최근 몇 개 봉의 최고/최저 종가를 기준으로 볼지 설정합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="breakout_pct",
                    label="진입 돌파 비율",
                    kind="number",
                    helper_text="0.02면 최근 최고 종가보다 2% 위에서 진입합니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="exit_breakdown_pct",
                    label="청산 이탈 비율",
                    kind="number",
                    helper_text="0이면 최근 최저 종가 이탈 즉시 청산합니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
            ),
        )

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
