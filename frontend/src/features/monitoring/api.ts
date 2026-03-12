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
  last_7d_return_pct: number;
  last_signal_at: string | null;
}

export interface UniverseSymbol {
  symbol: string;
  turnover_24h_krw: number;
  surge_score: number;
  selected: boolean;
  active_compare_session_count: number;
  has_open_position: boolean;
  has_recent_signal: boolean;
  risk_blocked: boolean;
}

export interface RiskOverviewItem {
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
