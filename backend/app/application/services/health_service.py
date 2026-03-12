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

    def settings_summary(self, runtime_status: dict[str, object]) -> dict[str, object]:
        return {
            "upbit": {
                "rest_base_url": self.settings.upbit_rest_base_url,
                "ws_public_url": self.settings.upbit_ws_public_url,
                "ws_private_url": self.settings.upbit_ws_private_url,
                "access_key_configured": bool(self.settings.upbit_access_key),
                "secret_key_configured": bool(self.settings.upbit_secret_key),
            },
            "storage": {
                "store_backend": self.settings.store_backend,
                "database_configured": bool(self.settings.database_url),
            },
            "live_protection": {
                "live_trading_enabled": self.settings.live_trading_enabled,
                "live_require_order_test": self.settings.live_require_order_test,
                "live_order_notional_krw": self.settings.live_order_notional_krw,
            },
            "runtime": runtime_status,
        }
