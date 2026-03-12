import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { Strategy, StrategyVersion } from '@/entities/strategy/types'
import type { ApiResponse } from '@/shared/types/api'

export const strategyKeys = {
  all: ['strategies'] as const,
  lists: () => [...strategyKeys.all, 'list'] as const,
  list: (filters: string) => [...strategyKeys.lists(), { filters }] as const,
  details: () => [...strategyKeys.all, 'detail'] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
  versions: (id: string) => [...strategyKeys.detail(id), 'versions'] as const,
}

export function useStrategies() {
  return useQuery({
    queryKey: strategyKeys.lists(),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Strategy[]>>('/strategies')
      return data.data
    },
  })
}

export function useStrategy(id: string) {
  return useQuery({
    queryKey: strategyKeys.detail(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<Strategy>>(`/strategies/${id}`)
      return data.data
    },
    enabled: !!id,
  })
}

export function useCreateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: Partial<Strategy>) => {
      const response = await apiClient.post<unknown, ApiResponse<Strategy>>('/strategies', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: strategyKeys.lists() })
    },
  })
}

export function useStrategyVersions(id: string) {
  return useQuery({
    queryKey: strategyKeys.versions(id),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<StrategyVersion[]>>(`/strategies/${id}/versions`)
      return data.data
    },
    enabled: !!id,
  })
}

export function useValidateVersion() {
  return useMutation({
    mutationFn: async ({ versionId, config_json }: { versionId: string, config_json: Record<string, unknown> }) => {
      const response = await apiClient.post<unknown, ApiResponse<{ is_valid: boolean, errors: string[], warnings: string[] }>>(`/strategy-versions/${versionId}/validate`, { config_json })
      return response.data
    },
  })
}
