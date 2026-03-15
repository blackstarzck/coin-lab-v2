import { createContext, createElement, type ReactNode, startTransition, useContext, useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { env } from '@/shared/config/env'
import { monitoringKeys, type MonitoringSummary } from './api'

interface MonitoringSnapshotMessage {
  type: 'monitoring_snapshot'
  data: MonitoringSummary
  timestamp: string
  trace_id: string
}

interface MonitoringHeartbeatMessage {
  type: 'heartbeat'
  timestamp: string
  trace_id: string
}

type MonitoringStreamMessage = MonitoringSnapshotMessage | MonitoringHeartbeatMessage

interface MonitoringSummaryStreamContextValue {
  isConnected: boolean
}

const MonitoringSummaryStreamContext = createContext<MonitoringSummaryStreamContextValue>({
  isConnected: false,
})

function toMonitoringWebSocketUrl(baseUrl: string): string {
  const resolvedBaseUrl = baseUrl || window.location.origin
  const url = new URL(resolvedBaseUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/monitoring'
  return url.toString()
}

export function MonitoringSummaryStreamProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    let websocket: WebSocket | null = null
    let reconnectTimer: number | null = null
    let reconnectAttempt = 0
    let isDisposed = false

    const clearReconnectTimer = () => {
      if (reconnectTimer === null) {
        return
      }
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    const connect = () => {
      if (isDisposed || websocket !== null) {
        return
      }

      clearReconnectTimer()
      const nextSocket = new WebSocket(toMonitoringWebSocketUrl(env.API_BASE_URL))
      websocket = nextSocket

      nextSocket.onopen = () => {
        if (websocket !== nextSocket) {
          return
        }
        reconnectAttempt = 0
        setIsConnected(true)
      }

      nextSocket.onmessage = (event) => {
        if (websocket !== nextSocket) {
          return
        }

        const message = JSON.parse(event.data) as MonitoringStreamMessage
        if (message.type !== 'monitoring_snapshot') {
          return
        }

        startTransition(() => {
          queryClient.setQueryData(monitoringKeys.summary(), message.data)
        })
      }

      nextSocket.onerror = () => {
        if (nextSocket.readyState === WebSocket.CONNECTING || nextSocket.readyState === WebSocket.OPEN) {
          nextSocket.close()
        }
      }

      nextSocket.onclose = () => {
        if (websocket === nextSocket) {
          websocket = null
        }

        if (isDisposed) {
          return
        }

        setIsConnected(false)
        const delayMs = Math.min(5_000, 500 * (2 ** reconnectAttempt))
        reconnectAttempt += 1
        reconnectTimer = window.setTimeout(() => {
          connect()
        }, delayMs)
      }
    }

    connect()

    return () => {
      isDisposed = true
      clearReconnectTimer()
      const currentSocket = websocket
      websocket = null
      if (currentSocket && (currentSocket.readyState === WebSocket.CONNECTING || currentSocket.readyState === WebSocket.OPEN)) {
        currentSocket.close()
      }
    }
  }, [queryClient])

  return createElement(
    MonitoringSummaryStreamContext.Provider,
    { value: { isConnected } },
    children,
  )
}

export function useMonitoringSummaryStream() {
  return useContext(MonitoringSummaryStreamContext)
}
