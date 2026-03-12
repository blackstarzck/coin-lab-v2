from __future__ import annotations

from ...infrastructure.repositories.lab_store import LabStore


class MonitoringService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

    def get_summary(self) -> dict[str, object]:
        sessions = self.store.list_sessions()
        strategies = self.store.list_strategies()
        running = [item for item in sessions if item.status.value == "RUNNING"]
        paper = [item for item in running if item.mode.value == "PAPER"]
        live = [item for item in running if item.mode.value == "LIVE"]
        failed = [item for item in sessions if item.status.value == "FAILED"]
        return {
            "status_bar": {
                "running_session_count": len(running),
                "paper_session_count": len(paper),
                "live_session_count": len(live),
                "failed_session_count": len(failed),
                "degraded_session_count": 0,
                "active_symbol_count": 0,
            },
            "strategy_cards": [
                {
                    "strategy_id": strategy.id,
                    "strategy_key": strategy.strategy_key,
                    "strategy_name": strategy.name,
                    "strategy_type": strategy.strategy_type.value,
                    "latest_version_id": strategy.latest_version_id,
                    "latest_version_no": strategy.latest_version_no,
                    "is_active": strategy.is_active,
                    "is_validated": False,
                    "active_session_count": 0,
                    "last_7d_return_pct": strategy.last_7d_return_pct,
                    "last_signal_at": None,
                }
                for strategy in strategies
            ],
            "universe_summary": {
                "active_symbol_count": 0,
                "watchlist_symbol_count": 0,
                "with_open_position_count": 0,
                "with_recent_signal_count": 0,
                "symbols": [],
            },
            "risk_overview": {
                "active_alert_count": 0,
                "blocked_signal_count_1h": 0,
                "daily_loss_limit_session_count": 0,
                "max_drawdown_session_count": 0,
                "items": [],
            },
            "recent_signals": [],
        }
