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

export interface UniverseCatalogItem {
  symbol: string
  korean_name: string
  english_name: string
  market_warning: string | null
  turnover_24h_krw: number
  trade_price: number | null
}

export const universeKeys = {
  all: ['universe'] as const,
  current: () => [...universeKeys.all, 'current'] as const,
  catalog: (quote: string, query: string, limit: number) => [...universeKeys.all, 'catalog', quote, query, limit] as const,
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

export function useUniverseCatalog({
  quote = 'KRW',
  query = '',
  limit = 10,
  enabled = true,
}: {
  quote?: string
  query?: string
  limit?: number
  enabled?: boolean
}) {
  return useQuery({
    queryKey: universeKeys.catalog(quote, query, limit),
    queryFn: async () => {
      const response = await apiClient.get<unknown, ApiResponse<UniverseCatalogItem[]>>('/universe/catalog', {
        params: {
          quote,
          query: query || undefined,
          limit,
        },
      })
      return response.data
    },
    enabled,
  })
}
