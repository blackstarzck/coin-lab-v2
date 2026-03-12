export interface CandlePoint {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartSnapshot {
  symbol: string;
  timeframe: string;
  candles: CandlePoint[];
  indicators: Record<string, { time: string; value: number }[]>;
}

export interface MarketSymbol {
  symbol: string;
  base_asset: string;
  quote_asset: string;
  status: string;
  tick_size: number;
  lot_size: number;
}
