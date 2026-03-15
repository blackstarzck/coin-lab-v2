import { startTransition, useEffect, useMemo, useState } from 'react'
import { env } from '@/shared/config/env'

export interface LiveSymbolPrice {
  symbol: string
  price: number | null
  timestamp: string | null
  buy_entry_rate_pct: number | null
  sell_entry_rate_pct: number | null
  entry_rate_window_sec: number | null
}

interface PriceSnapshotMessage {
  type: 'price_snapshot'
  symbols: LiveSymbolPrice[]
  trace_id: string
}

interface PriceUpdateMessage {
  type: 'price_update'
  symbol: string
  price: number
  timestamp: string
  buy_entry_rate_pct: number | null
  sell_entry_rate_pct: number | null
  entry_rate_window_sec: number | null
  trace_id: string
}

interface PriceHeartbeatMessage {
  type: 'heartbeat'
  timestamp: string
  trace_id: string
}

type PriceStreamMessage = PriceSnapshotMessage | PriceUpdateMessage | PriceHeartbeatMessage

function normalizeSymbols(symbols: string[]): string[] {
  const seen = new Set<string>()
  const normalized: string[] = []

  symbols.forEach((symbol) => {
    const cleaned = symbol.trim()
    if (!cleaned || seen.has(cleaned)) {
      return
    }
    seen.add(cleaned)
    normalized.push(cleaned)
  })

  normalized.sort()
  return normalized
}

function toPriceWebSocketUrl(baseUrl: string, symbols: string[]): string {
  const resolvedBaseUrl = baseUrl || window.location.origin
  const url = new URL(resolvedBaseUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = '/ws/prices'
  url.searchParams.set('symbols', symbols.join(','))
  return url.toString()
}

export function useActiveSymbolPrices(symbols: string[]) {
  const [pricesBySymbol, setPricesBySymbol] = useState<Record<string, LiveSymbolPrice>>({})
  const [isConnected, setIsConnected] = useState(false)

  const symbolsKey = useMemo(() => normalizeSymbols(symbols).join(','), [symbols])
  const requestedSymbols = useMemo(() => (symbolsKey ? symbolsKey.split(',') : []), [symbolsKey])

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

    const resetState = () => {
      startTransition(() => {
        setPricesBySymbol({})
        setIsConnected(false)
      })
    }

    const connect = () => {
      if (isDisposed || websocket !== null) {
        return
      }

      clearReconnectTimer()

      if (!requestedSymbols.length) {
        resetState()
        return
      }

      const nextSocket = new WebSocket(toPriceWebSocketUrl(env.API_BASE_URL, requestedSymbols))
      websocket = nextSocket

      nextSocket.onopen = () => {
        if (websocket !== nextSocket) {
          return
        }

        reconnectAttempt = 0
        startTransition(() => {
          setIsConnected(true)
        })
      }

      nextSocket.onmessage = (event) => {
        if (websocket !== nextSocket) {
          return
        }

        const message = JSON.parse(event.data) as PriceStreamMessage

        if (message.type === 'price_snapshot') {
          const nextState = message.symbols.reduce<Record<string, LiveSymbolPrice>>((accumulator, item) => {
            accumulator[item.symbol] = item
            return accumulator
          }, {})

          startTransition(() => {
            setPricesBySymbol(nextState)
          })
          return
        }

        if (message.type === 'price_update') {
          startTransition(() => {
            setPricesBySymbol((previous) => ({
              ...previous,
              [message.symbol]: {
                symbol: message.symbol,
                price: message.price,
                timestamp: message.timestamp,
                buy_entry_rate_pct: message.buy_entry_rate_pct,
                sell_entry_rate_pct: message.sell_entry_rate_pct,
                entry_rate_window_sec: message.entry_rate_window_sec,
              },
            }))
          })
        }
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

        if (isDisposed || !requestedSymbols.length) {
          return
        }

        startTransition(() => {
          setIsConnected(false)
        })

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
  }, [requestedSymbols, symbolsKey])

  return { pricesBySymbol, isConnected }
}
