import { startTransition, useEffect, useEffectEvent, useRef, useState } from 'react'
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

function toMonitoringWebSocketUrl(baseUrl: string): string {
  const resolvedBaseUrl = baseUrl || window.location.origin
  const url = new URL(resolvedBaseUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/monitoring'
  return url.toString()
}

export function useMonitoringSummaryStream() {
  const queryClient = useQueryClient()
  const websocketRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<number | null>(null)
  const reconnectAttemptRef = useRef(0)
  const shouldReconnectRef = useRef(true)
  const [isConnected, setIsConnected] = useState(false)

  const clearReconnectTimer = useEffectEvent(() => {
    if (reconnectTimerRef.current === null) {
      return
    }
    window.clearTimeout(reconnectTimerRef.current)
    reconnectTimerRef.current = null
  })

  const handleMessage = useEffectEvent((event: MessageEvent<string>) => {
    const message = JSON.parse(event.data) as MonitoringStreamMessage
    if (message.type !== 'monitoring_snapshot') {
      return
    }
    startTransition(() => {
      queryClient.setQueryData(monitoringKeys.summary(), message.data)
    })
  })

  const connect = useEffectEvent(() => {
    clearReconnectTimer()
    const websocket = new WebSocket(toMonitoringWebSocketUrl(env.API_BASE_URL))
    websocketRef.current = websocket

    websocket.onopen = () => {
      reconnectAttemptRef.current = 0
      setIsConnected(true)
    }

    websocket.onmessage = handleMessage

    websocket.onerror = () => {
      websocket.close()
    }

    websocket.onclose = () => {
      setIsConnected(false)
      websocketRef.current = null
      if (!shouldReconnectRef.current) {
        return
      }

      const delayMs = Math.min(5_000, 500 * (2 ** reconnectAttemptRef.current))
      reconnectAttemptRef.current += 1
      reconnectTimerRef.current = window.setTimeout(() => {
        connect()
      }, delayMs)
    }
  })

  useEffect(() => {
    shouldReconnectRef.current = true
    connect()

    return () => {
      shouldReconnectRef.current = false
      clearReconnectTimer()
      websocketRef.current?.close()
      websocketRef.current = null
    }
  }, [clearReconnectTimer, connect])

  return { isConnected }
}
