import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { ApiResponse } from '@/shared/types/api'

export const monitoringKeys = {
  all: ['monitoring'] as const,
  summary: () => [...monitoringKeys.all, 'summary'] as const,
}

export interface StatusBar {
  running_session_count: number;
  paper_session_count: number;
  live_session_count: number;
  failed_session_count: number;
  degraded_session_count: number;
  active_symbol_count: number;
}

export interface StrategyCard {
  strategy_id: string;
  strategy_key: string;
  strategy_name: string;
  strategy_type: string;
  latest_version_id: string;
  latest_version_no: number;
  is_active: boolean;
  is_validated: boolean;
  active_session_count: number;
  last_7d_return_pct: number | null;
  last_signal_at: string | null;
}

export interface UniverseSymbol {
  symbol: string;
  turnover_24h_krw: number | null;
  surge_score: number | null;
  selected: boolean;
  active_compare_session_count: number;
  has_open_position: boolean;
  has_recent_signal: boolean;
  risk_blocked: boolean;
}

export interface RiskOverviewItem {
  id: string;
  session_id: string;
  severity: string;
  code: string;
  message: string;
  created_at: string;
}

export interface RecentSignal {
  id: string;
  session_id: string;
  strategy_version_id: string;
  symbol: string;
  action: string;
  signal_price: number;
  confidence: number;
  blocked: boolean;
  reason_codes: string[];
  snapshot_time: string;
}

export interface DashboardHero {
  title: string;
  subtitle: string;
  active_strategy_count: number;
  running_session_count: number;
  active_symbol_count: number;
  recent_trade_count: number;
  latest_event_at: string | null;
  headline_strategy_name: string | null;
}

export interface DashboardStrategyStripItem {
  strategy_id: string;
  label: string;
  sessions: number;
  return_pct: number;
  tone: 'success' | 'danger' | 'warning' | 'info' | 'default' | string;
}

export interface DashboardMarketStripItem {
  symbol: string;
  selected: boolean;
  is_active: boolean;
  risk_blocked: boolean;
}

export interface DashboardPerformancePoint {
  label: string;
  timestamp: string | null;
  value: number;
}

export interface DashboardPerformanceSeries {
  strategy_id: string;
  strategy_name: string;
  color: string;
  return_pct: number;
  points: DashboardPerformancePoint[];
}

export interface DashboardActivityItem {
  id: string;
  kind: 'signal' | 'order' | 'risk' | string;
  strategy_name: string;
  symbol: string | null;
  title: string;
  detail: string;
  occurred_at: string;
  tone: 'success' | 'danger' | 'warning' | 'info' | 'default' | string;
}

export interface DashboardRecentTrade {
  id: string;
  strategy_id: string | null;
  strategy_name: string;
  symbol: string;
  order_role: string;
  price: number;
  qty: number;
  filled_at: string;
  session_id: string;
}

export interface DashboardLeaderboardRow {
  strategy_id: string;
  strategy_name: string;
  strategy_type: string;
  active_session_count: number;
  account_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  return_pct: number;
  win_rate_pct: number | null;
  trades: number;
  risk_alert_count: number;
}

export interface DashboardOpenPositionPreview {
  symbol: string;
  side: string;
  quantity: number;
  avg_entry_price: number | null;
  unrealized_pnl_pct: number;
}

export interface DashboardStrategyEntryReadiness {
  symbol: string;
  buy_readiness_pct: number | null;
  sell_readiness_pct: number | null;
}

export interface DashboardStrategyDetail extends DashboardLeaderboardRow {
  paper_session_count: number;
  live_session_count: number;
  active_position_count: number;
  degraded_session_count: number;
  monitoring_state: 'idle' | 'running' | 'degraded' | string;
  tracked_symbols: string[];
  last_signal_at: string | null;
  description: string | null;
  open_positions: DashboardOpenPositionPreview[];
  entry_readiness?: DashboardStrategyEntryReadiness[];
}

export interface DashboardMarketDetail {
  symbol: string;
  turnover_24h_krw: number | null;
  surge_score: number | null;
  selected: boolean;
  active_compare_session_count: number;
  has_open_position: boolean;
  has_recent_signal: boolean;
  risk_blocked: boolean;
}

export interface DashboardPayload {
  hero: DashboardHero;
  strategy_strip: DashboardStrategyStripItem[];
  market_strip: DashboardMarketStripItem[];
  performance_history: {
    series: DashboardPerformanceSeries[];
    best_strategy_name: string | null;
  };
  live_activity: DashboardActivityItem[];
  recent_trades: DashboardRecentTrade[];
  leaderboard: DashboardLeaderboardRow[];
  strategy_details: DashboardStrategyDetail[];
  market_details: DashboardMarketDetail[];
}

export interface MonitoringSummary {
  status_bar: StatusBar;
  strategy_cards: StrategyCard[];
  universe_summary: {
    active_symbol_count: number;
    watchlist_symbol_count: number;
    with_open_position_count: number;
    with_recent_signal_count: number;
    symbols: UniverseSymbol[];
  };
  risk_overview: {
    active_alert_count: number;
    blocked_signal_count_1h: number;
    daily_loss_limit_session_count: number;
    max_drawdown_session_count: number;
    items: RiskOverviewItem[];
  };
  recent_signals: RecentSignal[];
  dashboard: DashboardPayload;
}

export function useMonitoringSummary() {
  return useQuery({
    queryKey: monitoringKeys.summary(),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<MonitoringSummary>>('/monitoring/summary')
      return data.data
    },
  })
}
