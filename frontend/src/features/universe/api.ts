import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { ApiResponse } from '@/shared/types/api'

export interface UniverseSymbolOption {
  symbol: string
  turnover_24h_krw: number
  surge_score: number
  selected: boolean
  active_compare_session_count: number
  has_open_position: boolean
  has_recent_signal: boolean
  risk_blocked: boolean
}

export const universeKeys = {
  all: ['universe'] as const,
  current: () => [...universeKeys.all, 'current'] as const,
}

export function useCurrentUniverse() {
  return useQuery({
    queryKey: universeKeys.current(),
    queryFn: async () => {
      const response = await apiClient.get<unknown, ApiResponse<UniverseSymbolOption[]>>('/universe/current')
      return response.data
    },
  })
}
