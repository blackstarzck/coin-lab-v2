from __future__ import annotations

from typing import Any

from app.application.strategy_runtime import ComposerContext, ZenithHazelComposer, draft_to_explain_payload, draft_to_strategy_decision
from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import PluginAction, StrategyDecision
from app.domain.interfaces.strategy_plugin import StrategyPlugin, StrategyPluginFieldDefinition, StrategyPluginMetadata

from .metadata import TIMEFRAME_OPTIONS, timeframe_field


class ZenithHazelV1Plugin(StrategyPlugin):
    plugin_id = "zenith_hazel_v1"
    plugin_version = "1.0.0"

    def __init__(self) -> None:
        self._composer = ZenithHazelComposer()

    def metadata(self) -> StrategyPluginMetadata:
        return StrategyPluginMetadata(
            plugin_id=self.plugin_id,
            label="Zenith Hazel V1",
            version=self.plugin_version,
            description="Zenith 계열 운용 로그를 현재 Coin Lab 엔진에 맞게 재구성한 regime-aware momentum 플러그인입니다. 상위 타임프레임 레짐을 먼저 판정하고, 추세 정렬과 돌파/거래량/모멘텀 컨플루언스가 맞을 때만 long 진입합니다.",
            default_config={
                "timeframe": "15m",
                "regime_timeframe": "1h",
                "regime_lookback": 12,
                "swing_width": 3,
                "breakout_lookback": 20,
                "momentum_lookback": 6,
                "ema_fast_length": 9,
                "ema_slow_length": 21,
                "atr_length": 14,
                "min_regime_confidence": 0.22,
                "min_signal_confidence": 0.72,
                "min_signal_score": 4,
                "breakout_buffer_pct": 0.001,
                "min_momentum_pct": 0.004,
                "volume_surge_ratio": 1.2,
                "min_close_strength": 0.58,
                "high_volatility_atr_pct": 0.03,
                "stop_buffer_pct": 0.002,
                "exit_breakdown_pct": 0.005,
                "rr_target": 2.0,
                "time_exit_bars": 24,
                "allow_high_volatility_breakout": False,
            },
            fields=(
                timeframe_field("신호를 계산할 메인 캔들 타임프레임입니다."),
                StrategyPluginFieldDefinition(
                    key="regime_timeframe",
                    label="레짐 타임프레임",
                    kind="select",
                    helper_text="Multi-Regime Detector 역할을 할 상위 타임프레임입니다.",
                    options=TIMEFRAME_OPTIONS,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="regime_lookback",
                    label="레짐 룩백",
                    kind="integer",
                    helper_text="상위 타임프레임 추세를 판정할 룩백 봉 수입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="swing_width",
                    label="스윙 폭",
                    kind="integer",
                    helper_text="스윙 고저점을 추적할 폭입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="breakout_lookback",
                    label="돌파 룩백",
                    kind="integer",
                    helper_text="직전 N개 봉 최고가를 돌파 기준으로 사용합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="momentum_lookback",
                    label="모멘텀 룩백",
                    kind="integer",
                    helper_text="현재 모멘텀을 계산할 기준 봉 수입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="ema_fast_length",
                    label="빠른 EMA",
                    kind="integer",
                    helper_text="단기 추세 정렬을 볼 EMA 길이입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="ema_slow_length",
                    label="느린 EMA",
                    kind="integer",
                    helper_text="장기 추세 정렬을 볼 EMA 길이입니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="min_regime_confidence",
                    label="최소 레짐 신뢰도",
                    kind="number",
                    helper_text="상위 레짐 판정이 이 값보다 낮으면 보수적으로 진입을 막습니다.",
                    step=0.01,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="min_signal_confidence",
                    label="최소 신호 신뢰도",
                    kind="number",
                    helper_text="최종 엔트리 confidence 하한입니다.",
                    step=0.01,
                    display="percent",
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="volume_surge_ratio",
                    label="거래량 배수",
                    kind="number",
                    helper_text="직전 평균 거래량 대비 몇 배 이상이어야 하는지 설정합니다.",
                    step=0.05,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="rr_target",
                    label="목표 R 배수",
                    kind="number",
                    helper_text="손절폭 대비 목표 보상 배수입니다.",
                    step=0.1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="time_exit_bars",
                    label="시간 청산 봉 수",
                    kind="integer",
                    helper_text="지정 봉 수가 지나면 시간 청산을 허용합니다.",
                    step=1,
                    summary=True,
                ),
                StrategyPluginFieldDefinition(
                    key="allow_high_volatility_breakout",
                    label="고변동 돌파 허용",
                    kind="boolean",
                    helper_text="레짐이 HIGH_VOLATILITY일 때도 강한 돌파 진입을 허용할지 설정합니다.",
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
