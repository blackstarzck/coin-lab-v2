// Session entity types aligned with API_PAYLOADS.md
import type { ExplainPayload } from '@/entities/strategy/dsl-types';

export type ExecutionMode = 'BACKTEST' | 'PAPER' | 'LIVE';
export type SessionStatus = 'PENDING' | 'RUNNING' | 'STOPPING' | 'STOPPED' | 'FAILED';
export type PositionState = 'NONE' | 'OPENING' | 'OPEN' | 'CLOSING' | 'CLOSED' | 'FAILED';
export type OrderState = 'CREATED' | 'SUBMITTED' | 'PARTIALLY_FILLED' | 'FILLED' | 'CANCELLED' | 'REJECTED' | 'EXPIRED' | 'FAILED';
export type SignalAction = 'ENTER' | 'EXIT';
export type OrderRole = 'ENTRY' | 'EXIT' | 'STOP_LOSS' | 'TAKE_PROFIT';
export type OrderType = 'MARKET' | 'LIMIT';
export type ConnectionState = 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'RECOVERED' | 'DEGRADED';

export interface SessionSymbolScope {
  mode?: string;
  sources?: string[];
  max_symbols?: number;
  active_symbols?: string[];
}

export interface SessionPerformance {
  symbol_performance?: Record<string, SymbolPerformance>;
  realized_pnl: number;
  realized_pnl_pct: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  trade_count?: number;
  win_rate_pct?: number;
  max_drawdown_pct?: number;
  initial_capital?: number;
}

export interface SymbolPerformance {
  realized_pnl?: number;
  realized_pnl_pct?: number;
  realized_cost_basis?: number;
  trade_count?: number;
  winning_trade_count?: number;
}

export interface SessionHealth {
  connection_state: string;
  snapshot_consistency: string;
  late_event_count_5m: number;
}

export interface Session {
  id: string;
  mode: ExecutionMode;
  status: SessionStatus;
  strategy_version_id: string;
  symbol_scope: SessionSymbolScope;
  performance?: SessionPerformance;
  health?: SessionHealth;
  started_at: string | null;
  ended_at: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface Signal {
  id: string;
  session_id: string;
  strategy_version_id: string;
  symbol: string;
  timeframe: string;
  action: SignalAction;
  signal_price: number;
  confidence: number;
  reason_codes: string[];
  snapshot_time: string;
  blocked: boolean;
  explain_payload?: ExplainPayload | null;
}

export interface Position {
  id: string;
  session_id?: string;
  strategy_version_id: string;
  symbol: string;
  position_state: PositionState;
  side: string;
  entry_time: string;
  avg_entry_price: number;
  quantity: number;
  stop_loss_price: number | null;
  take_profit_price: number | null;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
}

export interface Order {
  id: string;
  session_id: string;
  strategy_version_id: string;
  symbol: string;
  order_role: OrderRole;
  order_type: OrderType;
  order_state: OrderState;
  requested_price: number | null;
  executed_price: number | null;
  requested_qty: number;
  executed_qty: number;
  retry_count: number;
  submitted_at: string;
  filled_at: string | null;
}

export interface RiskEvent {
  id: string;
  session_id: string;
  strategy_version_id: string;
  severity: string;
  code: string;
  symbol: string | null;
  message: string;
  payload_preview: Record<string, unknown>;
  created_at: string;
}

export interface Performance {
  realized_pnl: number;
  realized_pnl_pct: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  trade_count: number;
  win_rate_pct: number;
  max_drawdown_pct: number;
}

export interface SessionReevaluateResult {
  accepted: boolean;
  session_id: string;
  requested_symbols: string[];
  evaluated_symbols: string[];
  skipped: Array<{
    symbol: string | null;
    reason_code: string;
    reason_detail: string;
  }>;
}
