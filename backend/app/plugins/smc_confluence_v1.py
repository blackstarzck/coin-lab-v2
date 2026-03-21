from __future__ import annotations

from typing import Any

from app.application.strategy_runtime import ComposerContext, SmcConfluenceComposer, draft_to_explain_payload, draft_to_strategy_decision
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin, StrategyPluginFieldDefinition, StrategyPluginMetadata

from .metadata import timeframe_field


class SmcConfluenceV1Plugin(StrategyPlugin):
    plugin_id = "smc_confluence_v1"
    plugin_version = "1.0.0"

    def __init__(self) -> None:
        self._composer = SmcConfluenceComposer()

    def metadata(self) -> StrategyPluginMetadata:
        return StrategyPluginMetadata(
            plugin_id=self.plugin_id,
            label="SMC Confluence V1",
            version=self.plugin_version,
            description="추세 맥락, 오더블럭, FVG 리테스트가 겹칠 때 진입하고 구조가 깨지면 청산하는 long-only confluence 플러그인입니다.",
            default_config={
                "timeframe": "5m",
                "trend_lookback": 12,
                "order_block_lookback": 8,
                "displacement_min_body_ratio": 0.55,
                "displacement_min_pct": 0.003,
                "fvg_gap_pct": 0.001,
                "zone_retest_tolerance_pct": 0.0015,
                "exit_zone_break_pct": 0.002,
                "min_confluence_score": 3,
                "require_order_block": False,
                "require_fvg": False,
                "require_confirmation": True,
            },
            fields=(
                timeframe_field("추세 맥락과 존 리테스트를 읽을 캔들 기준입니다."),
                StrategyPluginFieldDefinition(
                    key="trend_lookback",
                    label="추세 룩백 봉 수",
                    kind="integer",
                    helper_text="최근 몇 개 봉으로 상승 구조와 추세 맥락을 판정할지 정합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="order_block_lookback",
                    label="오더블럭 탐색 길이",
                    kind="integer",
                    helper_text="최근 몇 개 봉 안에서 유효한 오더블럭 후보를 찾을지 설정합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="displacement_min_body_ratio",
                    label="최소 변동성 몸통 비율",
                    kind="number",
                    helper_text="강한 변동 캔들로 볼 최소 몸통 비율입니다. 0.55면 몸통이 전체 레인지의 55% 이상이어야 합니다.",
                    step=0.01,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="displacement_min_pct",
                    label="최소 변동 폭",
                    kind="number",
                    helper_text="강한 변동 캔들의 최소 상승 폭입니다. 0.003이면 0.30% 이상 상승해야 합니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="fvg_gap_pct",
                    label="최소 FVG 갭 비율",
                    kind="number",
                    helper_text="3캔들 FVG로 인정할 최소 갭 비율입니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="zone_retest_tolerance_pct",
                    label="존 리테스트 허용 오차",
                    kind="number",
                    helper_text="오더블럭/FVG 존에 다시 닿았다고 볼 허용 오차입니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="exit_zone_break_pct",
                    label="존 이탈 청산 버퍼",
                    kind="number",
                    helper_text="구조 무효화 청산을 낼 때 존 하단 아래로 어느 정도 더 이탈해야 하는지 설정합니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="min_confluence_score",
                    label="최소 컨플루언스 점수",
                    kind="integer",
                    helper_text="추세, 오더블럭, FVG, 확인 캔들 중 몇 개가 겹쳐야 진입할지 정합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="require_order_block",
                    label="오더블럭 필수",
                    kind="boolean",
                    helper_text="항상 오더블럭 리테스트가 동반되어야만 진입하도록 강제합니다.",
                    display="boolean",
                ),
                StrategyPluginFieldDefinition(
                    key="require_fvg",
                    label="FVG 필수",
                    kind="boolean",
                    helper_text="항상 FVG 리테스트가 동반되어야만 진입하도록 강제합니다.",
                    display="boolean",
                ),
                StrategyPluginFieldDefinition(
                    key="require_confirmation",
                    label="확인 캔들 필수",
                    kind="boolean",
                    helper_text="반등 확인용 bullish confirmation candle이 있어야만 진입합니다.",
                    display="boolean",
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
