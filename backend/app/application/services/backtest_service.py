from __future__ import annotations

from datetime import UTC, datetime
from math import sqrt
from statistics import pstdev
from uuid import uuid4

from ...core.exceptions import NotFoundError
from ...core.trace import generate_trace_id
from ...domain.entities.market import CandleState, ConnectionState, MarketSnapshot
from ...domain.entities.session import (
    BacktestRun,
    BacktestTrade,
    ExecutionMode,
    FillResult,
    Position,
    Session,
    SessionStatus,
)
from ...infrastructure.repositories.lab_store import LabStore
from ...schemas.backtest import BacktestRunRequest
from .execution_service import ExecutionService
from .fill_engine import FillEngine
from .risk_guard_service import RiskGuardService
from .signal_generator import SignalGenerator
from .strategy_symbol_resolver import resolve_strategy_symbols


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_dt(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _as_float(value: object, fallback: float) -> float:
    return float(value) if isinstance(value, int | float) else fallback


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
        strategy_version = self.store.get_strategy_version(data.strategy_version_id)
        if strategy_version is None:
            raise NotFoundError("Strategy version not found", {"strategy_version_id": data.strategy_version_id})

        strategy_config = strategy_version.config_json
        backtest_config = strategy_config.get("backtest", {})
        initial_capital = 1_000_000.0
        if isinstance(backtest_config, dict):
            capital_value = backtest_config.get("initial_capital")
            if isinstance(capital_value, (int, float)):
                initial_capital = float(capital_value)

        symbols = resolve_strategy_symbols(
            data.symbols,
            strategy_config,
            (
                str(item.get("symbol"))
                for item in self.store.get_current_universe()
                if isinstance(item, dict) and item.get("symbol")
            ),
        )

        run = BacktestRun(
            id=f"btr_{uuid4().hex[:12]}",
            status="QUEUED",
            strategy_version_id=data.strategy_version_id,
            symbols=symbols,
            timeframes=data.timeframes,
            date_from=_normalize_dt(data.date_from),
            date_to=_normalize_dt(data.date_to),
            initial_capital=initial_capital,
            metrics=self._default_metrics(),
            created_at=_now(),
            completed_at=None,
        )
        created = self.store.create_backtest_run(run)

        snapshots = self._normalize_snapshot_series(data.execution_overrides.get("snapshot_series"), symbols, data.timeframes)
        if snapshots:
            created.status = "RUNNING"
            self.store.update_backtest_run(created)
            trades, metrics = self._simulate_replay_run(created, strategy_config, snapshots)
            if trades:
                self.store.create_backtest_trades_bulk(trades)
            created.status = "COMPLETED"
            created.metrics = metrics
            created.completed_at = _now()
            self.store.update_backtest_run(created)

        return created

    def get_trades(self, run_id: str) -> list[BacktestTrade]:
        self.get_run(run_id)
        return self.store.list_backtest_trades(run_id)

    def get_performance(self, run_id: str) -> dict[str, object]:
        return self.get_run(run_id).metrics

    def get_equity_curve(self, run_id: str) -> list[dict[str, object]]:
        metrics = self.get_run(run_id).metrics
        equity_curve = metrics.get("equity_curve")
        return equity_curve if isinstance(equity_curve, list) else []

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

    def _simulate_replay_run(
        self,
        run: BacktestRun,
        strategy_config: dict[str, object],
        snapshots: list[MarketSnapshot],
    ) -> tuple[list[BacktestTrade], dict[str, object]]:
        risk_guard = RiskGuardService()
        fill_engine = FillEngine()
        signal_generator = SignalGenerator()
        execution_service = ExecutionService(risk_guard, fill_engine, signal_generator)
        session = Session(
            id=f"ses_bt_{run.id}",
            mode=ExecutionMode.BACKTEST,
            status=SessionStatus.RUNNING,
            strategy_version_id=run.strategy_version_id,
            symbol_scope_json={"active_symbols": run.symbols},
            risk_overrides_json={},
            config_snapshot=strategy_config,
            performance_json={"initial_capital": run.initial_capital},
            health_json={},
            trace_id=generate_trace_id(),
            started_at=run.created_at,
            ended_at=None,
            created_at=run.created_at,
            updated_at=run.created_at,
        )
        entry_fills: dict[str, FillResult] = {}
        trades: list[BacktestTrade] = []

        for snapshot in snapshots:
            result = execution_service.process_snapshot(session, strategy_config, snapshot)
            position = result.get("position")
            fill = result.get("fill")
            if isinstance(position, Position) and isinstance(fill, FillResult) and fill.filled:
                entry_fills[position.id] = fill

            exits = result.get("exits")
            if not isinstance(exits, list):
                continue
            for exit_result in exits:
                if not isinstance(exit_result, dict):
                    continue
                closed_position = exit_result.get("position")
                exit_fill = exit_result.get("fill")
                exit_reason = str(exit_result.get("exit_reason", "STRATEGY_EXIT"))
                if not isinstance(closed_position, Position) or not isinstance(exit_fill, FillResult) or not exit_fill.filled:
                    continue
                entry_fill = entry_fills.pop(closed_position.id, None)
                trades.append(
                    self._build_trade(
                        run_id=run.id,
                        position=closed_position,
                        entry_fill=entry_fill,
                        exit_fill=exit_fill,
                        exit_reason=exit_reason,
                        exit_time=snapshot.snapshot_time,
                    )
                )

        return trades, self._compute_metrics(run.initial_capital, trades)

    def _build_trade(
        self,
        *,
        run_id: str,
        position: Position,
        entry_fill: FillResult | None,
        exit_fill: FillResult,
        exit_reason: str,
        exit_time: datetime,
    ) -> BacktestTrade:
        entry_price = position.avg_entry_price or (entry_fill.fill_price if entry_fill is not None else 0.0) or 0.0
        exit_price = exit_fill.fill_price or entry_price
        qty = exit_fill.fill_qty
        gross_pnl = (exit_price - entry_price) * qty
        fee_amount = (entry_fill.fee_amount if entry_fill is not None else 0.0) + exit_fill.fee_amount
        slippage_amount = (entry_fill.slippage_amount if entry_fill is not None else 0.0) + exit_fill.slippage_amount
        pnl = gross_pnl - fee_amount
        pnl_pct = ((exit_price / entry_price) - 1.0) * 100 if entry_price > 0 else 0.0
        return BacktestTrade(
            id=f"btt_{uuid4().hex[:12]}",
            backtest_run_id=run_id,
            symbol=position.symbol,
            entry_time=position.entry_time or exit_time,
            exit_time=exit_time,
            entry_price=entry_price,
            exit_price=exit_price,
            qty=qty,
            pnl=pnl,
            pnl_pct=pnl_pct,
            fee_amount=fee_amount,
            slippage_amount=slippage_amount,
            exit_reason=exit_reason,
        )

    def _compute_metrics(self, initial_capital: float, trades: list[BacktestTrade]) -> dict[str, object]:
        if initial_capital <= 0:
            initial_capital = 1_000_000.0

        equity = initial_capital
        peak = initial_capital
        max_drawdown_pct = 0.0
        wins = 0
        gross_profit = 0.0
        gross_loss = 0.0
        hold_minutes_total = 0.0
        returns: list[float] = []
        equity_curve: list[dict[str, object]] = [
            {"time": _now().isoformat(), "equity": initial_capital, "drawdown_pct": 0.0}
        ]

        for trade in sorted(trades, key=lambda item: item.exit_time):
            equity += trade.pnl
            peak = max(peak, equity)
            drawdown_pct = ((equity - peak) / peak) * 100 if peak else 0.0
            max_drawdown_pct = min(max_drawdown_pct, drawdown_pct)
            equity_curve.append(
                {"time": trade.exit_time.isoformat(), "equity": round(equity, 6), "drawdown_pct": round(drawdown_pct, 6)}
            )
            hold_minutes_total += max((trade.exit_time - trade.entry_time).total_seconds() / 60.0, 0.0)
            trade_return = trade.pnl / initial_capital if initial_capital else 0.0
            returns.append(trade_return)
            if trade.pnl > 0:
                wins += 1
                gross_profit += trade.pnl
            elif trade.pnl < 0:
                gross_loss += abs(trade.pnl)

        trade_count = len(trades)
        total_return_pct = ((equity - initial_capital) / initial_capital) * 100 if initial_capital else 0.0
        win_rate_pct = (wins / trade_count) * 100 if trade_count else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        avg_hold_minutes = hold_minutes_total / trade_count if trade_count else 0.0
        sharpe_ratio = self._sharpe_ratio(returns)

        metrics = self._default_metrics()
        metrics.update(
            {
                "total_return_pct": round(total_return_pct, 6),
                "max_drawdown_pct": round(max_drawdown_pct, 6),
                "win_rate_pct": round(win_rate_pct, 6),
                "profit_factor": round(profit_factor, 6),
                "trade_count": trade_count,
                "avg_hold_minutes": round(avg_hold_minutes, 6),
                "sharpe_ratio": round(sharpe_ratio, 6),
                "equity_curve": equity_curve,
            }
        )
        return metrics

    def _sharpe_ratio(self, returns: list[float]) -> float:
        if len(returns) < 2:
            return 0.0
        avg_return = sum(returns) / len(returns)
        stdev = pstdev(returns)
        if stdev == 0:
            return 0.0
        return (avg_return / stdev) * sqrt(len(returns))

    def _default_metrics(self) -> dict[str, object]:
        return {
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "trade_count": 0,
            "avg_hold_minutes": 0.0,
            "sharpe_ratio": 0.0,
            "equity_curve": [],
        }

    def _normalize_snapshot_series(
        self,
        raw_series: object,
        default_symbols: list[str],
        timeframes: list[str],
    ) -> list[MarketSnapshot]:
        if not isinstance(raw_series, list):
            return []
        default_symbol = default_symbols[0] if default_symbols else "KRW-BTC"
        default_timeframe = timeframes[0] if timeframes else "1m"
        snapshots: list[MarketSnapshot] = []
        for item in raw_series:
            if not isinstance(item, dict):
                continue
            symbol = str(item.get("symbol", default_symbol))
            timeframe = str(item.get("timeframe", default_timeframe))
            candle_payload = item.get("candle") if isinstance(item.get("candle"), dict) else item
            candle = self._build_candle_state(symbol, timeframe, candle_payload)
            history_payload = item.get("history") or item.get("candle_history") or []
            history = tuple(
                self._build_candle_state(symbol, timeframe, history_item)
                for history_item in history_payload
                if isinstance(history_item, dict)
            )
            snapshot_time = _normalize_dt(item.get("snapshot_time", candle.candle_start.isoformat()))
            snapshots.append(
                MarketSnapshot(
                    symbol=symbol,
                    latest_price=_as_float(item.get("latest_price"), candle.close),
                    candles={timeframe: candle},
                    volume_24h=_as_float(item.get("volume_24h"), 0.0),
                    snapshot_time=snapshot_time,
                    candle_history={timeframe: history},
                    is_stale=False,
                    connection_state=ConnectionState.CONNECTED,
                    closed_timeframes=(timeframe,) if candle.is_closed else (),
                    updated_timeframes=(timeframe,),
                )
            )
        snapshots.sort(key=lambda snapshot: snapshot.snapshot_time)
        return snapshots

    def _build_candle_state(self, symbol: str, timeframe: str, payload: dict[str, object]) -> CandleState:
        candle_start = _normalize_dt(payload.get("candle_start", payload.get("snapshot_time", _now().isoformat())))
        close = _as_float(payload.get("close"), _as_float(payload.get("latest_price"), 0.0))
        open_price = _as_float(payload.get("open"), close)
        high = _as_float(payload.get("high"), max(open_price, close))
        low = _as_float(payload.get("low"), min(open_price, close))
        return CandleState(
            symbol=symbol,
            timeframe=timeframe,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=_as_float(payload.get("volume"), 0.0),
            candle_start=candle_start,
            is_closed=bool(payload.get("is_closed", True)),
            last_update=_normalize_dt(payload.get("last_update", candle_start.isoformat())),
        )
