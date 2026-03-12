export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  channel: string;
  message: string;
  metadata: Record<string, unknown>;
  trace_id: string | null;
  mode?: string | null;
  session_id?: string | null;
  strategy_version_id?: string | null;
  symbol?: string | null;
  event_type?: string;
}
