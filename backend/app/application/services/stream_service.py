from __future__ import annotations

class StreamService:
    def monitoring_snapshot(self) -> dict[str, object]:
        return {
            "status_bar": {
                "running_session_count": 0,
                "paper_session_count": 0,
                "live_session_count": 0,
                "failed_session_count": 0,
                "degraded_session_count": 0,
                "active_symbol_count": 4,
            }
        }

    def chart_snapshot(self, symbol: str, timeframe: str) -> dict[str, object]:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "points": [
                {
                    "time": "2026-03-11T15:55:00Z",
                    "open": 143120000,
                    "high": 143500000,
                    "low": 143000000,
                    "close": 143420000,
                    "volume": 12.34,
                }
            ],
        }

    def backtest_stream_event(self, run_id: str) -> dict[str, object]:
        return {"run_id": run_id, "status": "COMPLETED", "progress": 100}
