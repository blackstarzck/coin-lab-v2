import { useEffect, useState } from 'react'
import { env } from '@/shared/config/env'
import type { ChartSnapshot } from '@/entities/market/types'

export function useChartStream(symbol: string | null) {
  const [data, setData] = useState<ChartSnapshot | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  useEffect(() => {
    if (!symbol) return

    // Stub implementation
    console.log(`Connecting to chart stream for ${symbol} at ${env.API_BASE_URL.replace('http', 'ws')}/ws/charts/${symbol}`)
    setIsConnected(true)
    
    // Just to use setData to avoid TS error
    setData(null)

    return () => {
      console.log(`Disconnecting from chart stream for ${symbol}`)
      setIsConnected(false)
    }
  }, [symbol])

  return { data, isConnected }
}
