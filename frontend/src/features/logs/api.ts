import { useQuery } from '@tanstack/react-query'

import type { LogEntry } from '@/entities/log/types'
import { apiClient } from '@/shared/api/client'
import type { ApiResponse } from '@/shared/types/api'

export type LogChannel = 'system' | 'strategy-execution' | 'order-simulation' | 'risk-control' | 'documents'

interface LogEntryApiResponse {
  id: string
  channel: string
  level: LogEntry['level']
  trace_id: string | null
  mode?: string | null
  session_id?: string | null
  strategy_version_id?: string | null
  symbol?: string | null
  event_type?: string
  message: string
  payload: Record<string, unknown>
  logged_at: string
}

interface LogQueryOptions {
  refetchIntervalMs?: number
  enabled?: boolean
}

export const logKeys = {
  all: ['logs'] as const,
  list: (channel: LogChannel, sessionId?: string) => [...logKeys.all, channel, sessionId ?? 'all'] as const,
}

function mapLogEntry(entry: LogEntryApiResponse): LogEntry {
  return {
    id: entry.id,
    timestamp: entry.logged_at,
    level: entry.level,
    channel: entry.channel,
    message: entry.message,
    metadata: entry.payload,
    trace_id: entry.trace_id,
    mode: entry.mode ?? null,
    session_id: entry.session_id ?? null,
    strategy_version_id: entry.strategy_version_id ?? null,
    symbol: entry.symbol ?? null,
    event_type: entry.event_type,
  }
}

export function useLogs(channel: LogChannel, sessionId?: string, limit = 50, options?: LogQueryOptions) {
  return useQuery({
    queryKey: logKeys.list(channel, sessionId),
    queryFn: async () => {
      const response = await apiClient.get<unknown, ApiResponse<LogEntryApiResponse[]>>(`/logs/${channel}`, {
        params: {
          limit,
          ...(sessionId ? { session_id: sessionId } : {}),
        },
      })
      return response.data.map(mapLogEntry)
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchIntervalMs ?? false,
    refetchIntervalInBackground: Boolean(options?.refetchIntervalMs),
  })
}
