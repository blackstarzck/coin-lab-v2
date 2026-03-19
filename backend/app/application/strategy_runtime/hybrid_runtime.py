from __future__ import annotations

from app.domain.entities.market import MarketSnapshot
from app.domain.entities.strategy_decision import StrategyDecision
from app.domain.strategy_runtime import StrategyDecisionDraft

from .composers import ComposerContext, StrategyComposerRegistry
from .mappers import draft_to_explain_payload, draft_to_strategy_decision


class HybridStrategyRuntime:
    def __init__(self, composer_registry: StrategyComposerRegistry | None = None) -> None:
        self.composer_registry = composer_registry or StrategyComposerRegistry()

    def validate(self, strategy_config: dict[str, object]) -> None:
        composer = self._composer(strategy_config)
        composer.validate(self._composer_config(strategy_config))

    def evaluate_draft(self, strategy_config: dict[str, object], snapshot: MarketSnapshot) -> StrategyDecisionDraft:
        composer = self._composer(strategy_config)
        timeframe = self._primary_timeframe(strategy_config)
        context = ComposerContext(
            snapshot=snapshot,
            symbol=snapshot.symbol,
            timeframe=timeframe,
            config=self._composer_config(strategy_config),
            strategy_config=strategy_config,
        )
        return composer.compose(context)

    def evaluate(self, strategy_config: dict[str, object], snapshot: MarketSnapshot) -> StrategyDecision:
        draft = self.evaluate_draft(strategy_config, snapshot)
        return draft_to_strategy_decision(draft, snapshot)

    def explain(
        self,
        strategy_config: dict[str, object],
        snapshot: MarketSnapshot,
        *,
        fallback_decision: str | None = None,
        risk_blocks: list[str] | None = None,
    ) -> dict[str, object]:
        draft = self.evaluate_draft(strategy_config, snapshot)
        return draft_to_explain_payload(
            snapshot=snapshot,
            draft=draft,
            timeframe=self._primary_timeframe(strategy_config),
            fallback_decision=fallback_decision,
            risk_blocks=risk_blocks,
        )

    def _composer(self, strategy_config: dict[str, object]):
        hybrid = strategy_config.get("hybrid")
        hybrid_config = hybrid if isinstance(hybrid, dict) else strategy_config
        composer_id = hybrid_config.get("composer_id") or strategy_config.get("plugin_id")
        composer = self.composer_registry.get(str(composer_id) if isinstance(composer_id, str) else None)
        if composer is None:
            raise ValueError("composer_id must reference a registered strategy composer")
        return composer

    def _composer_config(self, strategy_config: dict[str, object]) -> dict[str, object]:
        hybrid = strategy_config.get("hybrid")
        hybrid_config = hybrid if isinstance(hybrid, dict) else strategy_config
        composer_config = hybrid_config.get("composer_config")
        if isinstance(composer_config, dict):
            return composer_config
        plugin_config = strategy_config.get("plugin_config")
        if isinstance(plugin_config, dict):
            return plugin_config
        return {}

    def _primary_timeframe(self, strategy_config: dict[str, object]) -> str:
        market = strategy_config.get("market")
        timeframes = market.get("timeframes") if isinstance(market, dict) and isinstance(market.get("timeframes"), list) else []
        return str(timeframes[0]) if timeframes else "1m"
