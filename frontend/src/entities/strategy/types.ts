export interface Strategy {
  id: string;
  strategy_key: string;
  name: string;
  strategy_type: 'dsl' | 'plugin' | 'hybrid';
  description: string | null;
  is_active: boolean;
  latest_version_id: string | null;
  latest_version_no: number | null;
  labels: string[];
  last_7d_return_pct: number | null;
  last_7d_win_rate: number | null;
  created_at: string;
  updated_at: string;
}

export interface StrategyVersion {
  id: string;
  strategy_id: string;
  version_no: number;
  schema_version: string;
  config_json: Record<string, unknown>;
  config_hash: string;
  labels: string[];
  notes: string | null;
  is_validated: boolean;
  created_at: string;
}
