import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { Session, Position, Order, Signal, RiskEvent, Performance, SessionReevaluateResult } from '@/entities/session/types'
import type { ApiResponse } from '@/shared/types/api'
import { logKeys } from '@/features/logs/api'
import { monitoringKeys } from '@/features/monitoring/api'

interface LiveQueryOptions {
  refetchIntervalMs?: number
  enabled?: boolean
}

function withLiveRefresh(refetchIntervalMs?: number): {
  refetchInterval: number | false
  refetchIntervalInBackground: boolean
} {
  return {
    refetchInterval: refetchIntervalMs ?? false,
    refetchIntervalInBackground: Boolean(refetchIntervalMs),
  }
}

export const sessionKeys = {
  all: ['sessions'] as const,
  lists: () => [...sessionKeys.all, 'list'] as const,
  list: (filters: string) => [...sessionKeys.lists(), { filters }] as const,
  details: () => [...sessionKeys.all, 'detail'] as const,
  detail: (id: string) => [...sessionKeys.details(), id] as const,
  positions: (id: string) => [...sessionKeys.detail(id), 'positions'] as const,
  orders: (id: string) => [...sessionKeys.detail(id), 'orders'] as const,
  signals: (id: string) => [...sessionKeys.detail(id), 'signals'] as const,
  riskEvents: (id: string) => [...sessionKeys.detail(id), 'risk-events'] as const,
  performance: (id: string) => [...sessionKeys.detail(id), 'performance'] as const,
}

export function useSessions(options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.lists(),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Session[]>>('/sessions')
      return data.data
    },
    enabled: options?.enabled ?? true,
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}

export function useSession(id: string, options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.detail(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Session>>(`/sessions/${id}`)
      return data.data
    },
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}

export function useCreateSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: Partial<Session>) => {
      const response = await apiClient.post<unknown, ApiResponse<Session>>('/sessions', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() })
    },
  })
}

export function useStopSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, reason = 'manual_stop' }: { id: string, reason?: string }) => {
      const response = await apiClient.post<unknown, ApiResponse<{ session_id: string }>>(`/sessions/${id}/stop`, { reason })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: sessionKeys.detail(variables.id) })
    },
  })
}

export function useKillSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      reason = 'operator_emergency',
      close_open_positions = true,
    }: {
      id: string
      reason?: string
      close_open_positions?: boolean
    }) => {
      const response = await apiClient.post<unknown, ApiResponse<{ session_id: string }>>(`/sessions/${id}/kill`, {
        reason,
        close_open_positions,
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: sessionKeys.detail(variables.id) })
    },
  })
}

export function useReevaluateSession() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      symbols,
    }: {
      id: string
      symbols?: string[]
    }) => {
      const response = await apiClient.post<unknown, ApiResponse<SessionReevaluateResult>>(`/sessions/${id}/reevaluate`, {
        symbols: symbols ?? [],
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: monitoringKeys.all })
      queryClient.invalidateQueries({ queryKey: sessionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: sessionKeys.detail(variables.id) })
      queryClient.invalidateQueries({ queryKey: sessionKeys.positions(variables.id) })
      queryClient.invalidateQueries({ queryKey: sessionKeys.orders(variables.id) })
      queryClient.invalidateQueries({ queryKey: sessionKeys.signals(variables.id) })
      queryClient.invalidateQueries({ queryKey: sessionKeys.riskEvents(variables.id) })
      queryClient.invalidateQueries({ queryKey: sessionKeys.performance(variables.id) })
      queryClient.invalidateQueries({ queryKey: logKeys.all })
    },
  })
}

export function useSessionPositions(id: string, options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.positions(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Position[]>>(`/sessions/${id}/positions`)
      return data.data
    },
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}

export function useSessionOrders(id: string, options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.orders(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Order[]>>(`/sessions/${id}/orders`)
      return data.data
    },
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}

export function useSessionSignals(id: string, options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.signals(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Signal[]>>(`/sessions/${id}/signals`)
      return data.data
    },
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}

export function useSessionRiskEvents(id: string, options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.riskEvents(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<RiskEvent[]>>(`/sessions/${id}/risk-events`)
      return data.data
    },
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}

export function useSessionPerformance(id: string, options?: LiveQueryOptions) {
  return useQuery({
    queryKey: sessionKeys.performance(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Performance>>(`/sessions/${id}/performance`)
      return data.data
    },
    enabled: Boolean(id) && (options?.enabled ?? true),
    ...withLiveRefresh(options?.refetchIntervalMs),
  })
}
