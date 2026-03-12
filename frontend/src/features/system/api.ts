import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { apiClient } from '@/shared/api/client'
import type { ApiResponse } from '@/shared/types/api'

export interface RuntimeStatus {
  running: boolean
  store_backend: string
  session_count: number
  running_session_count: number
  active_symbols: string[]
  connection_state: string
  reconnect_count_1h: number
}

export interface RuntimeSettings {
  upbit: {
    rest_base_url: string
    ws_public_url: string
    ws_private_url: string
    access_key_configured: boolean
    secret_key_configured: boolean
  }
  storage: {
    store_backend: string
    database_configured: boolean
  }
  live_protection: {
    live_trading_enabled: boolean
    live_require_order_test: boolean
    live_order_notional_krw: number
  }
  runtime: RuntimeStatus
}

export function useRuntimeStatus() {
  return useQuery({
    queryKey: ['runtime', 'status'],
    queryFn: async () => {
      const response = await apiClient.get<unknown, ApiResponse<RuntimeStatus>>('/runtime/status')
      return response.data
    },
  })
}

export function useRuntimeSettings() {
  return useQuery({
    queryKey: ['settings', 'runtime'],
    queryFn: async () => {
      const response = await apiClient.get<unknown, ApiResponse<RuntimeSettings>>('/settings/runtime')
      return response.data
    },
  })
}

export function useRuntimeToggle() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (running: boolean) => {
      const route = running ? '/runtime/start' : '/runtime/stop'
      const response = await apiClient.post<unknown, ApiResponse<RuntimeStatus>>(route)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runtime', 'status'] })
      queryClient.invalidateQueries({ queryKey: ['settings', 'runtime'] })
    },
  })
}
