import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/shared/api/client'
import type { Strategy, StrategyPluginMetadata, StrategyVersion, ValidationResult } from '@/entities/strategy/types'
import type { ApiResponse } from '@/shared/types/api'

export const strategyKeys = {
  all: ['strategies'] as const,
  lists: () => [...strategyKeys.all, 'list'] as const,
  list: (filters: string) => [...strategyKeys.lists(), { filters }] as const,
  details: () => [...strategyKeys.all, 'detail'] as const,
  detail: (id: string) => [...strategyKeys.details(), id] as const,
  versions: (id: string) => [...strategyKeys.detail(id), 'versions'] as const,
  plugins: () => [...strategyKeys.all, 'plugins'] as const,
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

export function useStrategyPlugins() {
  return useQuery({
    queryKey: strategyKeys.plugins(),
    queryFn: async () => {
      const data = await apiClient.get<unknown, ApiResponse<StrategyPluginMetadata[]>>('/strategies/plugins')
      return data.data
    },
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

export function useUpdateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...data }: Partial<Strategy> & { id: string }) => {
      const response = await apiClient.patch<unknown, ApiResponse<Strategy>>(`/strategies/${id}`, data)
      return response.data
    },
    onSuccess: (strategy) => {
      queryClient.invalidateQueries({ queryKey: strategyKeys.lists() })
      queryClient.invalidateQueries({ queryKey: strategyKeys.detail(strategy.id) })
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

export function useCreateStrategyVersion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      strategyId,
      data,
    }: {
      strategyId: string
      data: {
        schema_version: string
        config_json: Record<string, unknown>
        labels: string[]
        notes?: string | null
      }
    }) => {
      const response = await apiClient.post<unknown, ApiResponse<StrategyVersion>>(`/strategies/${strategyId}/versions`, data)
      return response.data
    },
    onSuccess: (version) => {
      queryClient.invalidateQueries({ queryKey: strategyKeys.versions(version.strategy_id) })
      queryClient.invalidateQueries({ queryKey: strategyKeys.detail(version.strategy_id) })
      queryClient.invalidateQueries({ queryKey: strategyKeys.lists() })
    },
  })
}

export function useValidateVersion() {
  return useMutation({
    mutationFn: async ({ versionId, strict = true }: { versionId: string, strict?: boolean }) => {
      const response = await apiClient.post<unknown, ApiResponse<ValidationResult>>(`/strategy-versions/${versionId}/validate`, { strict })
      return response.data
    },
  })
}

export function useValidateDraft() {
  return useMutation({
    mutationFn: async ({ configJson, strict = true }: { configJson: Record<string, unknown>, strict?: boolean }) => {
      const response = await apiClient.post<unknown, ApiResponse<ValidationResult>>('/strategies/validate-draft', {
        config_json: configJson,
        strict,
      })
      return response.data
    },
  })
}
