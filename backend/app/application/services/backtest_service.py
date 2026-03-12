from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from ...core.exceptions import NotFoundError
from ...domain.entities.session import BacktestRun, BacktestTrade
from ...infrastructure.repositories.lab_store import LabStore
from ...schemas.backtest import BacktestRunRequest


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class BacktestService:
    def __init__(self, store: LabStore) -> None:
        self.store = store

    def list_runs(self, page: int = 1, page_size: int = 20) -> tuple[list[BacktestRun], int]:
        rows = self.store.list_backtest_runs()
        total = len(rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return rows[start:end], total

    def get_run(self, run_id: str) -> BacktestRun:
        run = self.store.get_backtest_run(run_id)
        if run is None:
            raise NotFoundError("Backtest run not found", {"run_id": run_id})
        return run

    def create_run(self, data: BacktestRunRequest) -> BacktestRun:
        run = BacktestRun(
            id=f"btr_{uuid4().hex[:12]}",
            status="QUEUED",
            strategy_version_id=data.strategy_version_id,
            symbols=data.symbols,
            timeframes=data.timeframes,
            date_from=_normalize_dt(data.date_from),
            date_to=_normalize_dt(data.date_to),
            initial_capital=1000000,
            metrics={
                "total_return_pct": 12.45,
                "max_drawdown_pct": -4.2,
                "win_rate_pct": 57.14,
                "profit_factor": 1.62,
                "trade_count": 28,
                "avg_hold_minutes": 84.3,
                "sharpe_ratio": 1.18,
            },
            created_at=_now(),
            completed_at=None,
        )
        return self.store.create_backtest_run(run)

    def get_trades(self, run_id: str) -> list[BacktestTrade]:
        self.get_run(run_id)
        return self.store.list_backtest_trades(run_id)

    def get_performance(self, run_id: str) -> dict[str, object]:
        return self.get_run(run_id).metrics

    def get_equity_curve(self, run_id: str) -> list[dict[str, object]]:
        self.get_run(run_id)
        return [
            {"time": "2025-12-01T00:00:00Z", "equity": 1000000, "drawdown_pct": 0},
            {"time": "2026-01-15T00:00:00Z", "equity": 1078000, "drawdown_pct": -1.4},
            {"time": "2026-03-01T00:00:00Z", "equity": 1124500, "drawdown_pct": -4.2},
        ]

    def compare_runs(self, base_run_id: str, against_run_ids: list[str]) -> dict[str, object]:
        base_run = self.get_run(base_run_id)
        compared: list[dict[str, object]] = []
        for run_id in against_run_ids:
            run = self.get_run(run_id)
            compared.append(
                {
                    "run_id": run.id,
                    "total_return_pct": run.metrics.get("total_return_pct"),
                    "max_drawdown_pct": run.metrics.get("max_drawdown_pct"),
                    "win_rate_pct": run.metrics.get("win_rate_pct"),
                    "profit_factor": run.metrics.get("profit_factor"),
                    "trade_count": run.metrics.get("trade_count"),
                }
            )
        return {"base_run_id": base_run.id, "compared_runs": compared}

    def run_backtest(self, payload: BacktestRunRequest) -> dict[str, object]:
        run = self.create_run(payload)
        return {
            "run_id": run.id,
            "status": run.status,
            "strategy_version_id": run.strategy_version_id,
            "symbols": run.symbols,
            "date_from": run.date_from,
            "date_to": run.date_to,
            "queued_at": run.created_at,
        }

    def list_backtests(self, page: int = 1, page_size: int = 20) -> tuple[list[BacktestRun], int]:
        return self.list_runs(page, page_size)

    def get_backtest(self, run_id: str) -> BacktestRun:
        return self.get_run(run_id)

    def list_backtest_trades(self, run_id: str) -> list[BacktestTrade]:
        return self.get_trades(run_id)
