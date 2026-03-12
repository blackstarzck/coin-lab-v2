// Backtest entity types aligned with API_PAYLOADS.md

export type BacktestRunStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface BacktestMetrics {
  total_return_pct: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  profit_factor: number;
  trade_count: number;
  avg_hold_minutes: number;
  sharpe_ratio: number;
}

export interface BacktestRun {
  id: string;
  status: BacktestRunStatus;
  strategy_version_id: string;
  symbols: string[];
  timeframes: string[];
  date_from: string;
  date_to: string;
  initial_capital: number;
  metrics: BacktestMetrics;
  created_at: string;
  completed_at: string | null;
}

export interface BacktestTrade {
  id: string;
  backtest_run_id?: string;
  symbol: string;
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  qty: number;
  pnl: number;
  pnl_pct: number;
  fee_amount: number;
  slippage_amount: number;
  exit_reason: string;
}

export interface BacktestPerformance {
  total_return_pct: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  profit_factor: number;
  trade_count: number;
  avg_hold_minutes: number;
  sharpe_ratio: number;
}

export interface EquityCurvePoint {
  time: string;
  equity: number;
  drawdown_pct: number;
}

export interface BacktestCompareResult {
  base_run_id: string;
  compared_runs: Array<{
    run_id: string;
    total_return_pct: number;
    max_drawdown_pct: number;
    win_rate_pct: number;
    profit_factor: number;
    trade_count: number;
  }>;
}
