import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { BacktestRun, BacktestTrade, EquityCurvePoint } from '@/entities/backtest/types'
import type { ApiResponse } from '@/shared/types/api'

export const backtestKeys = {
  all: ['backtests'] as const,
  lists: () => [...backtestKeys.all, 'list'] as const,
  list: (filters: string) => [...backtestKeys.lists(), { filters }] as const,
  details: () => [...backtestKeys.all, 'detail'] as const,
  detail: (id: string) => [...backtestKeys.details(), id] as const,
  trades: (id: string) => [...backtestKeys.detail(id), 'trades'] as const,
  equityCurve: (id: string) => [...backtestKeys.detail(id), 'equity-curve'] as const,
}

export function useBacktests() {
  return useQuery({
    queryKey: backtestKeys.lists(),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<BacktestRun[]>>('/backtests')
      return data.data
    },
  })
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: backtestKeys.detail(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<BacktestRun>>(`/backtests/${id}`)
      return data.data
    },
    enabled: !!id,
  })
}

export function useRunBacktest() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: Partial<BacktestRun>) => {
      const response = await apiClient.post<unknown, ApiResponse<{
        run_id: string
        status: string
        strategy_version_id: string
        symbols: string[]
        date_from: string
        date_to: string
        queued_at: string
      }>>('/backtests/run', data)
      return {
        id: response.data.run_id,
        status: response.data.status,
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: backtestKeys.lists() })
    },
  })
}

export function useBacktestTrades(id: string) {
  return useQuery({
    queryKey: backtestKeys.trades(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<BacktestTrade[]>>(`/backtests/${id}/trades`)
      return data.data
    },
    enabled: !!id,
  })
}

export function useBacktestEquityCurve(id: string) {
  return useQuery({
    queryKey: backtestKeys.equityCurve(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<EquityCurvePoint[]>>(`/backtests/${id}/equity-curve`)
      return data.data
    },
    enabled: !!id,
  })
}
