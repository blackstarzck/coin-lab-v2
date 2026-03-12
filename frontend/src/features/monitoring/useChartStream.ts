import { startTransition, useEffect, useRef, useState } from 'react'
import { env } from '@/shared/config/env'
import type { ChartSnapshot } from '@/entities/market/types'

interface ChartSnapshotMessage {
  type: 'chart_snapshot'
  symbol: string
  timeframe: string
  points: ChartSnapshot['candles']
}

interface ChartPointMessage {
  type: 'chart_point'
  symbol: string
  timeframe: string
  point: ChartSnapshot['candles'][number]
}

type ChartStreamMessage = ChartSnapshotMessage | ChartPointMessage

function toWebSocketUrl(baseUrl: string, symbol: string, timeframe: string): string {
  const resolvedBaseUrl = baseUrl || window.location.origin
  const url = new URL(resolvedBaseUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `/ws/charts/${encodeURIComponent(symbol)}`
  url.searchParams.set('timeframe', timeframe)
  return url.toString()
}

export function useChartStream(symbol: string | null, timeframe: string) {
  const [data, setData] = useState<ChartSnapshot | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const websocketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!symbol) {
      websocketRef.current?.close()
      websocketRef.current = null
      startTransition(() => {
        setData(null)
        setIsConnected(false)
      })
      return
    }

    const ws = new WebSocket(toWebSocketUrl(env.API_BASE_URL, symbol, timeframe))
    websocketRef.current = ws

    ws.onopen = () => {
      startTransition(() => {
        setIsConnected(true)
      })
    }

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data) as ChartStreamMessage
      startTransition(() => {
        setData((prev) => {
          if (message.type === 'chart_snapshot') {
            return {
              symbol: message.symbol,
              timeframe: message.timeframe,
              candles: message.points,
              indicators: prev?.indicators ?? {},
            }
          }

          const previousCandles = prev?.candles ?? []
          const nextCandles = [...previousCandles]
          const existingIndex = nextCandles.findIndex((point) => point.time === message.point.time)

          if (existingIndex >= 0) {
            nextCandles[existingIndex] = message.point
          } else {
            nextCandles.push(message.point)
            nextCandles.sort((left, right) => new Date(left.time).getTime() - new Date(right.time).getTime())
          }

          return {
            symbol: message.symbol,
            timeframe: message.timeframe,
            candles: nextCandles,
            indicators: prev?.indicators ?? {},
          }
        })
      })
    }

    ws.onerror = () => {
      startTransition(() => {
        setIsConnected(false)
      })
    }

    ws.onclose = () => {
      startTransition(() => {
        setIsConnected(false)
      })
    }

    return () => {
      ws.close()
      if (websocketRef.current === ws) {
        websocketRef.current = null
      }
    }
  }, [symbol, timeframe])

  return { data, isConnected }
}
