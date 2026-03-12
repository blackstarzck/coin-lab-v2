from __future__ import annotations

from ...infrastructure.repositories.lab_store import LabStore


class UniverseService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

    def get_current(self) -> list[dict[str, object]]:
        rows = self.store.get_current_universe()
        return [
            {
                "symbol": str(item.get("symbol", "KRW-BTC")),
                "turnover_24h_krw": 152300000000,
                "surge_score": 0.93,
                "selected": True,
                "active_compare_session_count": 0,
                "has_open_position": False,
                "has_recent_signal": False,
                "risk_blocked": False,
            }
            for item in rows
        ]

    def preview(self, symbol_scope: dict[str, object]) -> dict[str, object]:
        raw_max_symbols = symbol_scope.get("max_symbols", 4)
        max_symbols = raw_max_symbols if isinstance(raw_max_symbols, int) else 4
        symbols = ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP"][:max_symbols]
        return {"symbols": symbols, "count": len(symbols)}
