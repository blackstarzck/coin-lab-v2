from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.repositories.lab_store import LabStore


class HealthService:
    def __init__(self, settings: Settings, store: LabStore) -> None:
        self.settings = settings
        self.store = store

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "app_env": self.settings.app_env,
            "store_backend": self.settings.store_backend,
            "strategy_count": len(self.store.list_strategies()),
        }

    def metadata_indicators(self) -> list[dict[str, object]]:
        return [{"id": "ema", "label": "EMA"}, {"id": "rsi", "label": "RSI"}]

    def metadata_strategy_operators(self) -> list[str]:
        return [
            "indicator_compare",
            "threshold_compare",
            "cross_over",
            "cross_under",
            "price_breakout",
            "volume_spike",
            "rsi_range",
            "candle_pattern",
            "regime_match",
        ]

    def metadata_timeframes(self) -> list[str]:
        return ["1m", "5m", "15m", "1h", "4h", "1d"]

    def metadata_markets(self) -> list[str]:
        return ["KRW", "BTC", "USDT"]
