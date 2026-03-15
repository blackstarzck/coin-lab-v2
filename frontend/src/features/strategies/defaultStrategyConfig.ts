type JsonObject = Record<string, unknown>

export const DEFAULT_STRATEGY_KEY = 'btc_breakout_v1'
export const DEFAULT_STRATEGY_NAME = 'BTC Breakout V1'

export function createDefaultStrategyConfig(): JsonObject {
  return {
    id: DEFAULT_STRATEGY_KEY,
    name: DEFAULT_STRATEGY_NAME,
    type: 'dsl',
    schema_version: '1.0.0',
    description: 'EMA trend plus breakout strategy',
    enabled: true,
    market: {
      exchange: 'UPBIT',
      market_types: ['KRW'],
      timeframes: ['5m', '15m'],
      trade_basis: 'candle',
      trigger: 'ON_CANDLE_CLOSE',
    },
    universe: {
      mode: 'static',
      symbols: ['KRW-BTC'],
      catalog_symbols: ['KRW-BTC'],
      max_symbols: 1,
      refresh_sec: 60,
      filters: {
        min_24h_turnover_krw: 1000000000,
        exclude_symbols: [],
      },
    },
    entry: {
      logic: 'all',
      conditions: [
        {
          type: 'indicator_compare',
          left: { kind: 'indicator', name: 'ema', params: { length: 20 } },
          operator: '>',
          right: { kind: 'indicator', name: 'ema', params: { length: 50 } },
        },
        {
          type: 'price_breakout',
          source: { kind: 'price', field: 'close' },
          operator: '>',
          reference: {
            kind: 'derived',
            name: 'highest_high',
            params: { lookback: 20, exclude_current: true },
          },
        },
      ],
    },
    reentry: {
      allow: false,
      cooldown_bars: 3,
      require_reset: true,
      reset_condition: {
        type: 'threshold_compare',
        left: { kind: 'price', field: 'close' },
        operator: '<',
        right: {
          kind: 'derived',
          name: 'highest_high',
          params: { lookback: 20, exclude_current: true },
        },
      },
    },
    position: {
      max_open_positions_per_symbol: 1,
      allow_scale_in: false,
      size_mode: 'fixed_percent',
      size_value: 0.1,
      size_caps: { min_pct: 0.02, max_pct: 0.1 },
      max_concurrent_positions: 4,
    },
    exit: {
      stop_loss_pct: 0.015,
      take_profit_pct: 0.03,
    },
    risk: {
      daily_loss_limit_pct: 0.03,
      max_strategy_drawdown_pct: 0.1,
      prevent_duplicate_entry: true,
      max_order_retries: 2,
      kill_switch_enabled: true,
    },
    execution: {
      entry_order_type: 'limit',
      exit_order_type: 'market',
      limit_timeout_sec: 15,
      fallback_to_market: true,
      slippage_model: 'fixed_bps',
      fee_model: 'per_fill',
    },
    backtest: {
      initial_capital: 1000000,
      fee_bps: 5,
      slippage_bps: 3,
      latency_ms: 200,
      fill_assumption: 'next_bar_open',
    },
    labels: ['trend', 'breakout'],
    notes: '',
  }
}
