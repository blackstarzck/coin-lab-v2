export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warning' | 'error' | 'critical';
  channel: string;
  message: string;
  metadata: Record<string, unknown>;
  trace_id: string | null;
}
