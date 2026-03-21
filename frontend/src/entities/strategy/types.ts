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

export type StrategyPluginFieldKind = 'select' | 'integer' | 'number' | 'boolean';
export type StrategyPluginFieldDisplay = 'raw' | 'percent' | 'boolean';

export interface StrategyPluginFieldOption {
  label: string;
  value: string;
}

export interface StrategyPluginFieldDefinition {
  key: string;
  label: string;
  kind: StrategyPluginFieldKind;
  helper_text: string;
  step?: number | null;
  display?: StrategyPluginFieldDisplay | null;
  options: StrategyPluginFieldOption[];
  summary: boolean;
}

export interface StrategyPluginMetadata {
  plugin_id: string;
  label: string;
  version: string;
  description: string;
  default_config: Record<string, string | number | boolean>;
  fields: StrategyPluginFieldDefinition[];
}

export interface ValidationIssue {
  code: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
}
