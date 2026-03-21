from __future__ import annotations

from typing import Any

from app.application.strategy_runtime import (
    ComposerContext,
    ObFvgBullReclaimComposer,
    draft_to_explain_payload,
    draft_to_strategy_decision,
)
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin, StrategyPluginFieldDefinition, StrategyPluginMetadata

from .metadata import TIMEFRAME_OPTIONS, timeframe_field


class ObFvgBullReclaimV1Plugin(StrategyPlugin):
    plugin_id = "ob_fvg_bull_reclaim_v1"
    plugin_version = "1.0.0"

    def __init__(self) -> None:
        self._composer = ObFvgBullReclaimComposer()

    def metadata(self) -> StrategyPluginMetadata:
        return StrategyPluginMetadata(
            plugin_id=self.plugin_id,
            label="OB FVG Bull Reclaim V1",
            version=self.plugin_version,
            description="1H 상승 구조를 필터로 두고, 15m 상승 임펄스에서 형성된 OB+FVG 되돌림을 양봉 마감으로 확인해 진입하는 현물 롱 전용 플러그인입니다.",
            default_config={
                "timeframe": "15m",
                "trend_timeframe": "1h",
                "swing_width": 3,
                "atr_length": 14,
                "atr_mult": 1.8,
                "body_ratio_threshold": 0.45,
                "ob_lookback": 8,
                "poi_expiry_bars": 24,
                "sl_buffer_pct": 0.001,
                "rr_target": 1.8,
                "time_exit_bars": 20,
                "require_prev_close": False,
                "bull_mode_off_exit_on_loss": True,
            },
            fields=(
                timeframe_field("진입 트리거와 POI 생성을 계산할 기준 타임프레임입니다."),
                StrategyPluginFieldDefinition(
                    key="trend_timeframe",
                    label="상위 추세 타임프레임",
                    kind="select",
                    helper_text="HH/HL Bull Mode를 계산할 상위 타임프레임입니다.",
                    options=TIMEFRAME_OPTIONS,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="swing_width",
                    label="스윙 폭",
                    kind="integer",
                    helper_text="상위 타임프레임에서 HH/HL 스윙 구조를 판정할 폭입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="atr_length",
                    label="ATR 길이",
                    kind="integer",
                    helper_text="강한 상승 임펄스 여부를 계산할 ATR 길이입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="atr_mult",
                    label="임펄스 ATR 배수",
                    kind="number",
                    helper_text="상승 임펄스를 인정할 최소 ATR 배수입니다.",
                    step=0.1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="body_ratio_threshold",
                    label="최소 몸통 비율",
                    kind="number",
                    helper_text="임펄스 캔들의 몸통이 전체 레인지에서 차지해야 하는 최소 비율입니다.",
                    step=0.01,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="ob_lookback",
                    label="OB 탐색 길이",
                    kind="integer",
                    helper_text="최근 몇 개 봉 안에서 마지막 음봉 오더블럭을 찾을지 설정합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="poi_expiry_bars",
                    label="POI 유효 봉 수",
                    kind="integer",
                    helper_text="형성된 OB+FVG POI를 몇 개 봉 동안 유효하게 볼지 설정합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="sl_buffer_pct",
                    label="손절 버퍼",
                    kind="number",
                    helper_text="OB 저점 아래 손절 버퍼입니다.",
                    step=0.001,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="rr_target",
                    label="목표 R 배수",
                    kind="number",
                    helper_text="진입가와 손절가 기준으로 계산할 목표 보상 배수입니다.",
                    step=0.1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="time_exit_bars",
                    label="시간 청산 봉 수",
                    kind="integer",
                    helper_text="지정한 봉 수 안에 청산되지 않으면 시간 청산합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="require_prev_close",
                    label="직전 종가 상향 마감 필수",
                    kind="boolean",
                    helper_text="리클레임 캔들이 직전 종가보다 높게 마감해야만 진입합니다.",
                    display="boolean",
                ),
                StrategyPluginFieldDefinition(
                    key="bull_mode_off_exit_on_loss",
                    label="Bull Mode 이탈 손실 청산",
                    kind="boolean",
                    helper_text="Bull Mode가 꺼지고 손실 상태면 런타임 청산을 허용합니다.",
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
                timeframe=str(plugin_config.get("timeframe", "15m")),
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
                timeframe=str(plugin_config.get("timeframe", "15m")),
                config=plugin_config,
            )
        )
        return draft_to_explain_payload(
            snapshot=snapshot,
            draft=draft,
            timeframe=str(plugin_config.get("timeframe", "15m")),
            fallback_decision=PluginAction.HOLD.value,
        )
