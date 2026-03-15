// Strategy DSL Types — aligned with STRATEGY_DSL_SPEC.md
// This is the canonical TypeScript shape for config_json

export type StrategyDSLType = 'dsl' | 'plugin' | 'hybrid';

// §5.1 SourceRef
export interface SourceRefPrice {
  kind: 'price';
  field: string;
}

export interface SourceRefIndicator {
  kind: 'indicator';
  name: string;
  params?: Record<string, number>;
}

export interface SourceRefDerived {
  kind: 'derived';
  name: string;
  params?: Record<string, unknown>;
}

export interface SourceRefConstant {
  kind: 'constant';
  value: number;
}

export type SourceRef = SourceRefPrice | SourceRefIndicator | SourceRefDerived | SourceRefConstant;

// §5.2 TimeframeRef
export interface TimeframeRef {
  base: string;
  compare_to?: string;
}

// §8 Comparison operators
export type ComparisonOperator = '>' | '>=' | '<' | '<=' | '==' | '!=';

// §9 Leaf operators
export interface IndicatorCompareLeaf {
  type: 'indicator_compare';
  left: SourceRef;
  operator: ComparisonOperator;
  right: SourceRef;
}

export interface ThresholdCompareLeaf {
  type: 'threshold_compare';
  left: SourceRef;
  operator: ComparisonOperator;
  right: SourceRef;
}

export interface CrossOverLeaf {
  type: 'cross_over';
  left: SourceRef;
  right: SourceRef;
  lookback_bars?: number;
}

export interface CrossUnderLeaf {
  type: 'cross_under';
  left: SourceRef;
  right: SourceRef;
  lookback_bars?: number;
}

export interface PriceBreakoutLeaf {
  type: 'price_breakout';
  source: SourceRef;
  operator: ComparisonOperator;
  reference: SourceRef;
}

export interface VolumeSpikeLeaf {
  type: 'volume_spike';
  source: SourceRef;
  operator: ComparisonOperator;
  threshold: number;
}

export interface RsiRangeLeaf {
  type: 'rsi_range';
  source: SourceRef;
  min: number;
  max: number;
}

export type CandlePatternName =
  | 'bullish_engulfing'
  | 'bearish_engulfing'
  | 'inside_bar_break'
  | 'long_lower_wick';

export interface CandlePatternLeaf {
  type: 'candle_pattern';
  pattern: CandlePatternName;
  timeframe: string;
}

export type RegimeType =
  | 'trend_up'
  | 'trend_down'
  | 'range'
  | 'high_volatility'
  | 'low_volatility';

export interface RegimeMatchLeaf {
  type: 'regime_match';
  regime: RegimeType;
}

export type LeafCondition =
  | IndicatorCompareLeaf
  | ThresholdCompareLeaf
  | CrossOverLeaf
  | CrossUnderLeaf
  | PriceBreakoutLeaf
  | VolumeSpikeLeaf
  | RsiRangeLeaf
  | CandlePatternLeaf
  | RegimeMatchLeaf;

// §8 Logic blocks
export interface AllBlock {
  logic: 'all';
  conditions: ConditionNode[];
}

export interface AnyBlock {
  logic: 'any';
  conditions: ConditionNode[];
}

export interface NotBlock {
  logic: 'not';
  condition: ConditionNode;
}

export type ConditionNode = AllBlock | AnyBlock | NotBlock | LeafCondition;

// §6 Market section
export interface MarketSection {
  exchange: 'UPBIT';
  market_types: string[];
  timeframes: string[];
  trade_basis: 'candle' | 'tick' | 'hybrid';
}

// §7 Universe section
export type UniverseSource = 'top_turnover' | 'top_volume' | 'surge' | 'drop' | 'watchlist';

export interface UniverseFilters {
  min_24h_turnover_krw?: number;
  exclude_symbols?: string[];
}

export interface UniverseSection {
  mode: 'dynamic' | 'static';
  sources?: UniverseSource[];
  symbols?: string[];
  catalog_symbols?: string[];
  max_symbols?: number;
  refresh_sec?: number;
  filters?: UniverseFilters;
}

// §11 Reentry section
export interface ReentrySection {
  allow: boolean;
  cooldown_bars?: number;
  require_reset?: boolean;
  reset_condition?: ConditionNode;
}

// §12 Position section
export type SizeMode = 'fixed_amount' | 'fixed_percent' | 'fractional_kelly' | 'risk_per_trade';

export interface SizeCaps {
  min_pct: number;
  max_pct: number;
}

export interface PositionSection {
  max_open_positions_per_symbol: number;
  allow_scale_in: boolean;
  size_mode: SizeMode;
  size_value: number;
  size_caps?: SizeCaps;
  max_concurrent_positions: number;
}

// §13 Exit section
export interface PartialTakeProfit {
  at_profit_pct: number;
  close_ratio: number;
}

export interface ExitSection {
  stop_loss_pct?: number;
  take_profit_pct?: number;
  trailing_stop_pct?: number;
  time_stop_bars?: number;
  partial_take_profits?: PartialTakeProfit[];
  logic?: 'all' | 'any' | 'not';
  conditions?: ConditionNode[];
  condition?: ConditionNode;
}

// §14 Risk section
export interface RiskSection {
  daily_loss_limit_pct: number;
  max_strategy_drawdown_pct: number;
  prevent_duplicate_entry: boolean;
  max_order_retries: number;
  kill_switch_enabled: boolean;
}

// §15 Execution section
export type SlippageModel = 'none' | 'fixed_bps' | 'volatility_scaled';
export type FeeModel = 'per_fill' | 'per_order';

export interface ExecutionSection {
  entry_order_type: 'market' | 'limit';
  exit_order_type: 'market' | 'limit';
  limit_timeout_sec?: number;
  fallback_to_market?: boolean;
  slippage_model: SlippageModel;
  fee_model: FeeModel;
}

// §16 Backtest section
export type FillAssumption = 'best_bid_ask' | 'mid' | 'next_tick' | 'next_bar_open';

export interface BacktestSection {
  initial_capital: number;
  fee_bps: number;
  slippage_bps: number;
  latency_ms: number;
  fill_assumption: FillAssumption;
}

// §17 Explain payload
export interface ExplainFact {
  label: string;
  value: string | number | boolean | null;
}

export interface ExplainPayload {
  snapshot_key: string;
  decision: string;
  reason_codes: string[];
  facts: ExplainFact[];
  parameters?: ExplainFact[];
  matched_conditions: string[];
  failed_conditions: string[];
  risk_blocks: string[];
  legacy_payload?: boolean;
  legacy_note?: string | null;
}

// §4 Full DSL root
export interface StrategyDSL {
  id: string;
  name: string;
  type: StrategyDSLType;
  schema_version: string;
  description?: string;
  enabled?: boolean;
  market: MarketSection;
  universe: UniverseSection;
  entry: ConditionNode;
  reentry?: ReentrySection;
  position: PositionSection;
  exit: ExitSection;
  risk: RiskSection;
  execution: ExecutionSection;
  backtest: BacktestSection;
  labels?: string[];
  notes?: string;
}
