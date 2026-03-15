import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Skeleton,
  Stack,
  Button,
  Tabs,
  Tab,
  Tooltip,
  Divider
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, StopCircle, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import {
  useSessions,
  useSession,
  useSessionPositions,
  useSessionOrders,
  useSessionSignals,
  useSessionRiskEvents,
  useStopSession,
  useKillSession,
  useReevaluateSession,
} from '@/features/sessions/api'
import { useMonitoringSummary } from '@/features/monitoring/api'
import type { StrategyCard } from '@/features/monitoring/api'
import { EventLogHelpPopover } from '@/features/monitoring/EventLogHelpPopover'
import { useStrategies } from '@/features/strategies/api'
import { useUiStore } from '@/stores/ui-store'
import { CandlestickChart } from '@/shared/charts/CandlestickChart'
import { useChartStream } from '@/features/monitoring/useChartStream'
import { useActiveSymbolPrices } from '@/features/monitoring/useActiveSymbolPrices'
import { StrategyExplainPanel } from '@/features/monitoring/StrategyExplainPanel'
import { useEffect, useMemo, useState } from 'react'
import { useLogs } from '@/features/logs/api'
import {
  formatTime,
  translateConnectionState,
  translateLogChannel,
  translateLogLevel,
  translateMode,
  translateOrderRole,
  translateOrderState,
  translateSessionStatus,
  translateSignalAction,
} from '@/shared/lib/i18n'
import { apiClient } from '@/shared/api/client'
import type { StrategyVersion } from '@/entities/strategy/types'
import type { ApiResponse } from '@/shared/types/api'
import { resolveChartIndicatorSettings } from '@/shared/charts/chartIndicators'
import { StatusText } from '@/shared/ui/StatusText'
import { useAnimatedTableRows } from '@/shared/ui/useAnimatedTableRows'

const DETAIL_REFRESH_INTERVAL_MS = 2_000
const POSITION_REFRESH_INTERVAL_MS = 5_000
const SESSION_REFRESH_INTERVAL_MS = 5_000
const SESSION_LIST_REFRESH_INTERVAL_MS = 10_000

export default function MonitoringPage() {
  const navigate = useNavigate()
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)
  const [bottomTab, setBottomTab] = useState(0)
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null)

  const shouldLoadEventLogs = bottomTab === 0
  const shouldLoadStrategyExplain = bottomTab === 1
  const shouldLoadSignals = bottomTab === 2
  const shouldLoadOrders = bottomTab === 3
  const shouldLoadRiskEvents = bottomTab === 4
  const shouldLoadSignalData = shouldLoadStrategyExplain || shouldLoadSignals

  const { data: sessions, isLoading: isLoadingSessions } = useSessions({ refetchIntervalMs: SESSION_LIST_REFRESH_INTERVAL_MS })
  const { data: monitoringSummary } = useMonitoringSummary()
  const { data: strategies, isLoading: isLoadingStrategies } = useStrategies()
  
  const { 
    selectedSessionId, 
    setSelectedSession, 
    selectedSymbol, 
    setSelectedSymbol,
    chartTimeframe,
    setChartTimeframe,
    chartOverlays,
    toggleChartOverlay
  } = useUiStore()

  const activeSessionId = useMemo(() => {
    if (selectedSessionId && sessions?.some((currentSession) => currentSession.id === selectedSessionId)) {
      return selectedSessionId
    }
    return sessions?.[0]?.id || ''
  }, [selectedSessionId, sessions])
  const { data: session } = useSession(activeSessionId, { refetchIntervalMs: SESSION_REFRESH_INTERVAL_MS })
  const { data: positions } = useSessionPositions(activeSessionId, { refetchIntervalMs: POSITION_REFRESH_INTERVAL_MS })
  const { data: orders } = useSessionOrders(activeSessionId, {
    enabled: shouldLoadOrders,
    refetchIntervalMs: shouldLoadOrders ? DETAIL_REFRESH_INTERVAL_MS : undefined,
  })
  const { data: signals } = useSessionSignals(activeSessionId, {
    enabled: shouldLoadSignalData,
    refetchIntervalMs: shouldLoadSignalData ? DETAIL_REFRESH_INTERVAL_MS : undefined,
  })
  const { data: riskEvents } = useSessionRiskEvents(activeSessionId, {
    enabled: shouldLoadRiskEvents,
    refetchIntervalMs: shouldLoadRiskEvents ? DETAIL_REFRESH_INTERVAL_MS : undefined,
  })
  const { data: strategyExecutionLogs } = useLogs('strategy-execution', activeSessionId, 50, {
    enabled: shouldLoadEventLogs,
    refetchIntervalMs: shouldLoadEventLogs ? DETAIL_REFRESH_INTERVAL_MS : undefined,
  })
  const { data: orderSimulationLogs } = useLogs('order-simulation', activeSessionId, 50, {
    enabled: shouldLoadEventLogs,
    refetchIntervalMs: shouldLoadEventLogs ? DETAIL_REFRESH_INTERVAL_MS : undefined,
  })
  const { data: riskControlLogs } = useLogs('risk-control', activeSessionId, 50, {
    enabled: shouldLoadEventLogs,
    refetchIntervalMs: shouldLoadEventLogs ? DETAIL_REFRESH_INTERVAL_MS : undefined,
  })
  const stopSession = useStopSession()
  const killSession = useKillSession()
  const reevaluateSession = useReevaluateSession()

  const availableSymbols = useMemo(
    () => session?.symbol_scope?.active_symbols || [],
    [session?.symbol_scope?.active_symbols],
  )
  const activeSymbol = selectedSymbol && availableSymbols.includes(selectedSymbol)
    ? selectedSymbol
    : availableSymbols[0] || null

  const { data: chartData } = useChartStream(activeSymbol, chartTimeframe)
  const { pricesBySymbol } = useActiveSymbolPrices(availableSymbols)

  const eventTimeline = useMemo(() => (
    [
      ...(strategyExecutionLogs ?? []),
      ...(orderSimulationLogs ?? []),
      ...(riskControlLogs ?? []),
    ].sort((left, right) => {
      const timeCompare = new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime()
      if (timeCompare !== 0) {
        return timeCompare
      }
      return right.id.localeCompare(left.id)
    })
  ), [orderSimulationLogs, riskControlLogs, strategyExecutionLogs])
  const orderedSignals = useMemo(
    () => [...(signals ?? [])].sort((left, right) => {
      const timeCompare = new Date(right.snapshot_time).getTime() - new Date(left.snapshot_time).getTime()
      if (timeCompare !== 0) {
        return timeCompare
      }
      return right.id.localeCompare(left.id)
    }),
    [signals],
  )

  const eventLogRowIds = useMemo(() => eventTimeline.map((log) => `${log.channel}:${log.id}`), [eventTimeline])
  const signalRowIds = useMemo(() => orderedSignals.map((signal) => signal.id), [orderedSignals])
  const orderRowIds = useMemo(() => orders?.map((order) => order.id) ?? [], [orders])
  const riskRowIds = useMemo(() => riskEvents?.map((event) => event.id) ?? [], [riskEvents])
  const { setRowRef: setEventLogRowRef } = useAnimatedTableRows(eventLogRowIds)
  const { setRowRef: setSignalRowRef } = useAnimatedTableRows(signalRowIds)
  const { setRowRef: setOrderRowRef } = useAnimatedTableRows(orderRowIds)
  const { setRowRef: setRiskRowRef } = useAnimatedTableRows(riskRowIds)

  useEffect(() => {
    if (activeSessionId && selectedSessionId !== activeSessionId) {
      setSelectedSession(activeSessionId)
    }
  }, [activeSessionId, selectedSessionId, setSelectedSession])

  useEffect(() => {
    if (selectedSymbol && availableSymbols.includes(selectedSymbol)) {
      return
    }
    setSelectedSymbol(availableSymbols[0] ?? null)
  }, [availableSymbols, selectedSymbol, setSelectedSymbol])

  useEffect(() => {
    if (!activeSessionId && selectedSessionId) {
      setSelectedSession(null)
    }
  }, [activeSessionId, selectedSessionId, setSelectedSession])

  useEffect(() => {
    if (bottomTab > 4) {
      setBottomTab(4)
    }
  }, [bottomTab])

  useEffect(() => {
    if (!orderedSignals.length) {
      if (selectedSignalId !== null) {
        setSelectedSignalId(null)
      }
      return
    }

    if (!selectedSignalId || !orderedSignals.some((signal) => signal.id === selectedSignalId)) {
      setSelectedSignalId(orderedSignals[0].id)
    }
  }, [orderedSignals, selectedSignalId])

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'PAPER': return 'info'
      case 'LIVE': return 'error'
      case 'BACKTEST': return 'default'
      default: return 'default'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'RUNNING': return 'success'
      case 'STOPPED': return 'default'
      case 'FAILED': return 'error'
      case 'PENDING': return 'warning'
      default: return 'default'
    }
  }

  const getConnectionColor = (state: string) => {
    switch (state) {
      case 'CONNECTED': return 'success'
      case 'DISCONNECTED': return 'error'
      case 'RECONNECTING': return 'warning'
      case 'DEGRADED': return 'warning'
      default: return 'default'
    }
  }

  const getActionTone = (action: string): 'success' | 'danger' => {
    return action === 'ENTER' ? 'success' : 'danger'
  }

  const getPnlTone = (value: number): 'success' | 'danger' | 'default' => {
    if (value > 0) {
      return 'success'
    }
    if (value < 0) {
      return 'danger'
    }
    return 'default'
  }

  const getSessionStatusTone = (status: string): 'success' | 'warning' | 'info' | 'danger' | 'default' => {
    switch (status) {
      case 'RUNNING':
        return 'success'
      case 'PENDING':
        return 'info'
      case 'STOPPING':
        return 'warning'
      case 'FAILED':
        return 'danger'
      default:
        return 'default'
    }
  }

  const asNumber = (value: unknown) => {
    const parsed = typeof value === 'number' ? value : Number(value)
    return Number.isFinite(parsed) ? parsed : 0
  }

  const formatSignedAmount = (value: number) => `${value > 0 ? '+' : ''}${Math.round(value).toLocaleString()}`
  const formatSignedPercent = (value: number) => `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
  const formatChartPrice = (value: number) => Math.round(value).toLocaleString('ko-KR')

  const strategyIds = useMemo(
    () => (strategies ?? []).map((strategy) => strategy.id).sort(),
    [strategies],
  )

  const { data: strategyVersionBundles, isLoading: isLoadingStrategyVersions } = useQuery({
    queryKey: ['monitoring', 'strategy-version-bundles', strategyIds],
    queryFn: async () =>
      Promise.all(
        (strategies ?? []).map(async (strategy) => {
          const response = await apiClient.get<unknown, ApiResponse<StrategyVersion[]>>(`/strategies/${strategy.id}/versions`)
          return {
            strategy,
            versions: response.data,
          }
        }),
      ),
    enabled: strategyIds.length > 0,
    staleTime: 60_000,
  })

  const strategyCardByVersionId = useMemo(() => {
    const cardMap = new Map<string, StrategyCard>()

    ;(monitoringSummary?.strategy_cards ?? []).forEach((card) => {
      if (card.latest_version_id) {
        cardMap.set(card.latest_version_id, card)
      }
    })

    return cardMap
  }, [monitoringSummary?.strategy_cards])

  const strategyMetaByVersionId = useMemo(() => {
    const versionMap = new Map<
      string,
      {
        strategyId: string
        strategyName: string
        strategyKey: string
        strategyDescription: string | null
        versionNo: number
        isValidated: boolean
      }
    >()

    ;(strategyVersionBundles ?? []).forEach(({ strategy, versions }) => {
      versions.forEach((version) => {
        versionMap.set(version.id, {
          strategyId: strategy.id,
          strategyName: strategy.name,
          strategyKey: strategy.strategy_key,
          strategyDescription: strategy.description,
          versionNo: version.version_no,
          isValidated: version.is_validated,
        })
      })
    })

    return versionMap
  }, [strategyVersionBundles])

  const strategyConfigByVersionId = useMemo(() => {
    const configMap = new Map<string, Record<string, unknown>>()

    ;(strategyVersionBundles ?? []).forEach(({ versions }) => {
      versions.forEach((version) => {
        configMap.set(version.id, version.config_json ?? {})
      })
    })

    return configMap
  }, [strategyVersionBundles])

  const sessionsWithStrategy = useMemo(() => {
    const sessionStatusRank = (status: string) => {
      switch (status) {
        case 'RUNNING':
          return 0
        case 'PENDING':
          return 1
        case 'STOPPING':
          return 2
        case 'FAILED':
          return 3
        case 'STOPPED':
          return 4
        default:
          return 5
      }
    }

    return (sessions ?? [])
      .map((currentSession) => {
        const versionMeta = strategyMetaByVersionId.get(currentSession.strategy_version_id)
        const fallbackCard = strategyCardByVersionId.get(currentSession.strategy_version_id)
        const fallbackStrategyId = `version:${currentSession.strategy_version_id}`

        return {
          session: currentSession,
          strategyId: versionMeta?.strategyId ?? fallbackCard?.strategy_id ?? fallbackStrategyId,
          strategyName: versionMeta?.strategyName ?? fallbackCard?.strategy_name ?? `전략 v${currentSession.strategy_version_id.split('-')[0]}`,
          strategyKey: versionMeta?.strategyKey ?? fallbackCard?.strategy_key ?? currentSession.strategy_version_id.split('-')[0],
          strategyDescription: versionMeta?.strategyDescription ?? null,
          versionNo: versionMeta?.versionNo ?? fallbackCard?.latest_version_no ?? null,
          isValidated: versionMeta?.isValidated ?? Boolean(fallbackCard?.is_validated),
          strategyReturnPct: fallbackCard?.last_7d_return_pct ?? null,
        }
      })
      .sort((left, right) => {
        const strategyCompare = left.strategyName.localeCompare(right.strategyName)
        if (strategyCompare !== 0) {
          return strategyCompare
        }

        const statusCompare = sessionStatusRank(left.session.status) - sessionStatusRank(right.session.status)
        if (statusCompare !== 0) {
          return statusCompare
        }

        return (right.session.started_at ?? '').localeCompare(left.session.started_at ?? '')
      })
  }, [sessions, strategyCardByVersionId, strategyMetaByVersionId])

  const strategyGroups = useMemo(() => {
    const grouped = new Map<
      string,
      {
        strategyId: string
        strategyName: string
        strategyKey: string
        strategyDescription: string | null
        sessions: typeof sessionsWithStrategy
        versionLabels: Set<string>
        runningSessionCount: number
        latestSessionStartedAt: string | null
        strategyReturnPct: number | null
        isNavigable: boolean
      }
    >()

    sessionsWithStrategy.forEach((entry) => {
      const group = grouped.get(entry.strategyId)
      const versionLabel = entry.versionNo ? `v${entry.versionNo}` : `v${entry.session.strategy_version_id.split('-')[0]}`
      const sessionStartedAt = entry.session.started_at ?? entry.session.created_at ?? null

      if (group) {
        group.sessions.push(entry)
        group.versionLabels.add(versionLabel)
        group.runningSessionCount += entry.session.status === 'RUNNING' ? 1 : 0
        if (sessionStartedAt && (!group.latestSessionStartedAt || sessionStartedAt > group.latestSessionStartedAt)) {
          group.latestSessionStartedAt = sessionStartedAt
        }
        return
      }

      grouped.set(entry.strategyId, {
        strategyId: entry.strategyId,
        strategyName: entry.strategyName,
        strategyKey: entry.strategyKey,
        strategyDescription: entry.strategyDescription,
        sessions: [entry],
        versionLabels: new Set([versionLabel]),
        runningSessionCount: entry.session.status === 'RUNNING' ? 1 : 0,
        latestSessionStartedAt: sessionStartedAt,
        strategyReturnPct: entry.strategyReturnPct,
        isNavigable: !entry.strategyId.startsWith('version:'),
      })
    })

    return Array.from(grouped.values())
      .map((group) => ({
        ...group,
        versionSummary: group.versionLabels.size === 1
          ? Array.from(group.versionLabels)[0]
          : `버전 ${group.versionLabels.size}개`,
      }))
      .sort((left, right) => {
        if (right.runningSessionCount !== left.runningSessionCount) {
          return right.runningSessionCount - left.runningSessionCount
        }

        return left.strategyName.localeCompare(right.strategyName)
      })
  }, [sessionsWithStrategy])

  const activeSessionEntry = useMemo(
    () => sessionsWithStrategy.find((entry) => entry.session.id === activeSessionId) ?? null,
    [activeSessionId, sessionsWithStrategy],
  )

  const activeStrategyConfig = useMemo(
    () => (session ? strategyConfigByVersionId.get(session.strategy_version_id) ?? null : null),
    [session, strategyConfigByVersionId],
  )

  const activeIndicatorSettings = useMemo(
    () => resolveChartIndicatorSettings(activeStrategyConfig),
    [activeStrategyConfig],
  )

  const selectedStrategyGroup = useMemo(
    () => strategyGroups.find((group) => group.strategyId === selectedStrategyId) ?? null,
    [selectedStrategyId, strategyGroups],
  )

  const filteredSessionEntries = useMemo(() => {
    if (!selectedStrategyId) {
      return sessionsWithStrategy
    }
    return sessionsWithStrategy.filter((entry) => entry.strategyId === selectedStrategyId)
  }, [selectedStrategyId, sessionsWithStrategy])

  useEffect(() => {
    if (!strategyGroups.length) {
      if (selectedStrategyId !== null) {
        setSelectedStrategyId(null)
      }
      return
    }

    if (activeSessionEntry?.strategyId) {
      if (selectedStrategyId !== activeSessionEntry.strategyId) {
        setSelectedStrategyId(activeSessionEntry.strategyId)
      }
      return
    }

    if (!selectedStrategyId || !strategyGroups.some((group) => group.strategyId === selectedStrategyId)) {
      setSelectedStrategyId(strategyGroups[0].strategyId)
    }
  }, [activeSessionEntry, selectedStrategyId, strategyGroups])

  const symbolPerformanceRows = useMemo(() => {
    const positionBySymbol = new Map()
    const openPositionStates = new Set(['OPENING', 'OPEN', 'CLOSING'])

    positions?.forEach((position) => {
      if (!openPositionStates.has(position.position_state)) {
        return
      }
      positionBySymbol.set(position.symbol, position)
    })

    return availableSymbols.map((symbol) => {
      const position = positionBySymbol.get(symbol)
      const latestPrice = pricesBySymbol[symbol]?.price
      const avgEntryPrice = asNumber(position?.avg_entry_price)
      const quantity = asNumber(position?.quantity)
      const canUseLivePrice =
        typeof latestPrice === 'number'
        && Number.isFinite(latestPrice)
        && avgEntryPrice > 0
        && quantity > 0

      const pnlAmount = canUseLivePrice
        ? (latestPrice - avgEntryPrice) * quantity
        : asNumber(position?.unrealized_pnl)
      const pnlPercent = canUseLivePrice
        ? ((latestPrice - avgEntryPrice) / avgEntryPrice) * 100
        : asNumber(position?.unrealized_pnl_pct)

      return {
        symbol,
        pnlAmount,
        pnlPercent,
      }
    })
  }, [availableSymbols, positions, pricesBySymbol])

  const activeSymbolSignals = useMemo(
    () => orderedSignals.filter((signal) => signal.symbol === activeSymbol),
    [activeSymbol, orderedSignals],
  )

  const latestCandle = useMemo(() => {
    if (!chartData?.candles?.length) {
      return null
    }
    return chartData.candles[chartData.candles.length - 1] ?? null
  }, [chartData])

  const chartTimeframeOptions = [
    { value: '1m', label: '1' },
    { value: '5m', label: '5' },
    { value: '15m', label: '15' },
    { value: '1h', label: '1H' },
  ] as const

  const neutralIndicatorChipSx = {
    height: 24,
    fontSize: 11,
    fontWeight: 500,
    color: '#cbd5e1',
    bgcolor: 'transparent',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: 999,
  } as const

  const handleStrategySelect = (strategyId: string) => {
    setSelectedStrategyId(strategyId)

    const targetGroup = strategyGroups.find((group) => group.strategyId === strategyId)
    const nextSession = targetGroup?.sessions[0]?.session

    if (nextSession && nextSession.id !== activeSessionId) {
      setSelectedSession(nextSession.id)
      setSelectedSymbol(null)
    }
  }

  const handleSessionSelect = (sessionId: string) => {
    setSelectedSession(sessionId)
    setSelectedSymbol(null)

    const nextEntry = sessionsWithStrategy.find((entry) => entry.session.id === sessionId)
    if (nextEntry && nextEntry.strategyId !== selectedStrategyId) {
      setSelectedStrategyId(nextEntry.strategyId)
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 2, gap: 2 }}>
      {/* Top Global Bar */}
      <Card sx={{ flexShrink: 0 }}>
        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 }, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="h6" sx={{ mr: 2 }}>모니터링</Typography>
            {session ? (
              <>
                <Chip 
                  label={translateMode(session.mode)} 
                  size="small" 
                  sx={{ 
                    bgcolor: getModeColor(session.mode) === 'default' ? 'action.disabledBackground' : `status.${getModeColor(session.mode)}`,
                    color: getModeColor(session.mode) === 'default' ? 'text.secondary' : 'white'
                  }} 
                />
                <Chip 
                  label={translateSessionStatus(session.status)} 
                  size="small" 
                  variant="outlined"
                  sx={{ 
                    borderColor: getStatusColor(session.status) === 'default' ? 'divider' : `status.${getStatusColor(session.status)}`,
                    color: getStatusColor(session.status) === 'default' ? 'text.secondary' : `status.${getStatusColor(session.status)}`
                  }} 
                />
                <Typography variant="body2" color="text.secondary" sx={{ fontFamily: 'monospace' }}>
                  {session.id.split('-')[0]}
                </Typography>
                <Divider orientation="vertical" flexItem />
                <Typography variant="body2" color="text.secondary">
                  {activeSessionEntry?.strategyName ?? `전략 v${session.strategy_version_id.split('-')[0]}`}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {activeSessionEntry?.versionNo ? `v${activeSessionEntry.versionNo}` : `v${session.strategy_version_id.split('-')[0]}`}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {session.started_at ? formatTime(session.started_at) : '시작 전'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  심볼 {availableSymbols.length}개
                </Typography>
                {session.health && (
                  <Chip 
                    label={translateConnectionState(session.health.connection_state)} 
                    size="small" 
                    variant="outlined" 
                    sx={{ 
                      ml: 2,
                      borderColor: getConnectionColor(session.health.connection_state) === 'default' ? 'divider' : `status.${getConnectionColor(session.health.connection_state)}`,
                      color: getConnectionColor(session.health.connection_state) === 'default' ? 'text.secondary' : `status.${getConnectionColor(session.health.connection_state)}`
                    }}
                  />
                )}
                {session.mode === 'LIVE' ? (
                  <Chip label="실전 안전장치 활성" size="small" color="error" />
                ) : null}
              </>
            ) : (
              <Typography color="text.secondary" variant="body2">선택된 세션이 없습니다</Typography>
            )}
          </Stack>
          
          <Stack direction="row" spacing={1}>
            {selectedStrategyGroup?.isNavigable ? (
              <Button
                variant="text"
                color="inherit"
                onClick={() => navigate(`/strategies/${selectedStrategyGroup.strategyId}`)}
              >
                전략 상세
              </Button>
            ) : null}
            <Button
              variant="outlined"
              color="inherit"
              startIcon={<RefreshCw size={16} />}
              disabled={!session || session.status !== 'RUNNING' || reevaluateSession.isPending}
              onClick={() => {
                if (session) {
                  reevaluateSession.mutate({
                    id: session.id,
                    symbols: activeSymbol ? [activeSymbol] : undefined,
                  })
                }
              }}
            >
              수동 재평가
            </Button>
            <Button 
              variant="outlined" 
              color="inherit" 
              startIcon={<StopCircle size={16} />}
              disabled={!session || session.status !== 'RUNNING'}
              onClick={() => {
                if (session) {
                  stopSession.mutate({ id: session.id, reason: 'manual_stop' })
                }
              }}
            >
              중지
            </Button>
            <Button 
              variant="contained" 
              color="error" 
              startIcon={<AlertTriangle size={16} />}
              disabled={!session || session.status !== 'RUNNING'}
              onClick={() => {
                if (session) {
                  killSession.mutate({ id: session.id, reason: 'operator_emergency', close_open_positions: true })
                }
              }}
            >
              긴급 종료
            </Button>
          </Stack>
        </CardContent>
      </Card>
      
      {/* 3-Column Layout */}
      <Box sx={{ display: 'flex', flexGrow: 1, gap: 2, minHeight: 0 }}>
        
        {/* Left Column - Strategy > Session > PnL */}
        <Box sx={{ width: 360, display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0, minHeight: 0 }}>
          <Card sx={{ minHeight: 220, maxHeight: 260, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" fontWeight={700}>
                전략
              </Typography>
              <Typography variant="caption" color="text.secondary">
                최근 7일 전략 성과
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1, minHeight: 0 }}>
              {isLoadingStrategies || isLoadingStrategyVersions ? (
                <Stack spacing={1} sx={{ p: 2 }}>
                  <Skeleton variant="rounded" height={40} />
                  <Skeleton variant="rounded" height={40} />
                  <Skeleton variant="rounded" height={40} />
                </Stack>
              ) : strategyGroups.length === 0 ? (
                <Box sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    세션과 연결된 전략이 없습니다
                  </Typography>
                </Box>
              ) : (
                <TableContainer sx={{ maxHeight: '100%' }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                        <TableCell>전략</TableCell>
                        <TableCell>버전</TableCell>
                        <TableCell align="right">세션</TableCell>
                        <TableCell align="right">7일</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {strategyGroups.map((group) => (
                        <TableRow
                          key={group.strategyId}
                          hover
                          onClick={() => handleStrategySelect(group.strategyId)}
                          sx={{
                            cursor: 'pointer',
                            bgcolor: selectedStrategyId === group.strategyId ? 'rgba(34, 231, 107, 0.05)' : 'transparent',
                          }}
                        >
                          <TableCell sx={{ minWidth: 0 }}>
                            <Typography variant="body2" fontWeight={700} noWrap>
                              {group.strategyName}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {group.strategyKey}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" color="text.secondary">
                              {group.versionSummary}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="caption" color="text.secondary">
                              {group.runningSessionCount}/{group.sessions.length}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            {group.strategyReturnPct === null ? (
                              <Typography variant="caption" color="text.disabled">
                                없음
                              </Typography>
                            ) : (
                              <StatusText tone={getPnlTone(group.strategyReturnPct)}>
                                {formatSignedPercent(group.strategyReturnPct)}
                              </StatusText>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Card>

          <Card sx={{ flexGrow: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" fontWeight={700}>
                세션
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {selectedStrategyGroup ? `${selectedStrategyGroup.strategyName}의 세션` : '전략을 먼저 선택하세요'}
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1, minHeight: 0 }}>
              {isLoadingSessions ? (
                <Stack spacing={1} sx={{ p: 2 }}>
                  <Skeleton variant="rounded" height={40} />
                  <Skeleton variant="rounded" height={40} />
                  <Skeleton variant="rounded" height={40} />
                </Stack>
              ) : filteredSessionEntries.length === 0 ? (
                <Box sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    선택한 전략의 세션이 없습니다
                  </Typography>
                </Box>
              ) : (
                <TableContainer sx={{ maxHeight: '100%' }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                        <TableCell>세션</TableCell>
                        <TableCell>버전</TableCell>
                        <TableCell>상태</TableCell>
                        <TableCell align="right">시작</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredSessionEntries.map(({ session: currentSession, versionNo }) => (
                        <TableRow
                          key={currentSession.id}
                          hover
                          onClick={() => handleSessionSelect(currentSession.id)}
                          sx={{
                            cursor: 'pointer',
                            bgcolor: activeSessionId === currentSession.id ? 'rgba(34, 231, 107, 0.05)' : 'transparent',
                          }}
                        >
                          <TableCell sx={{ minWidth: 0 }}>
                            <Typography variant="body2" fontFamily="monospace" noWrap>
                              {currentSession.id.split('-')[0]}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" noWrap>
                              {translateMode(currentSession.mode)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" color="text.secondary">
                              {versionNo ? `v${versionNo}` : `v${currentSession.strategy_version_id.split('-')[0]}`}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <StatusText tone={getSessionStatusTone(currentSession.status)}>
                              {translateSessionStatus(currentSession.status)}
                            </StatusText>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                              {currentSession.started_at ? formatTime(currentSession.started_at) : '시작 전'}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>
          </Card>

          <Card sx={{ minHeight: 220, maxHeight: 280, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Stack direction="row" spacing={0.75} alignItems="center">
                <Typography variant="subtitle2" fontWeight={700}>
                  수익 현황
                </Typography>
                <Tooltip title="초기 자금 100만원" placement="top" arrow>
                  <Box
                    component="span"
                    aria-label="초기 자금 정보"
                    sx={{
                      width: 18,
                      height: 18,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: '50%',
                      border: 1,
                      borderColor: 'divider',
                      color: 'text.secondary',
                      fontSize: 11,
                      fontWeight: 700,
                      lineHeight: 1,
                      cursor: 'help',
                    }}
                  >
                    i
                  </Box>
                </Tooltip>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {activeSessionEntry ? `${activeSessionEntry.strategyName} · ${activeSessionEntry.session.id.split('-')[0]}` : '선택된 세션 없음'}
              </Typography>
            </Box>
            <Box sx={{ flexGrow: 1, minHeight: 0 }}>
              <TableContainer sx={{ maxHeight: '100%' }}>
                <Table size="small" stickyHeader sx={{ '& .MuiTableCell-root': { py: 1, px: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>심볼</TableCell>
                      <TableCell align="right">수익률</TableCell>
                      <TableCell align="right">손익</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!symbolPerformanceRows.length ? (
                      <TableRow>
                        <TableCell colSpan={3} align="center" sx={{ py: 4 }}>
                          <Typography variant="body2" color="text.secondary">
                            생성된 성과가 없습니다
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      symbolPerformanceRows.map((row) => {
                        const pnlTone = getPnlTone(row.pnlAmount)

                        return (
                          <TableRow
                            key={row.symbol}
                            hover
                            onClick={() => setSelectedSymbol(row.symbol)}
                            sx={{
                              cursor: 'pointer',
                              bgcolor: activeSymbol === row.symbol ? 'rgba(34, 231, 107, 0.05)' : 'transparent',
                            }}
                          >
                            <TableCell>
                              <Typography variant="body2" fontWeight={700}>
                                {row.symbol}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <StatusText tone={getPnlTone(row.pnlPercent)} variant="body2">
                                {formatSignedPercent(row.pnlPercent)}
                              </StatusText>
                            </TableCell>
                            <TableCell align="right">
                              <StatusText tone={pnlTone} variant="body2">
                                {formatSignedAmount(row.pnlAmount)}
                              </StatusText>
                            </TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </Card>
        </Box>

        {/* Center Panel - Chart */}
        <Card
          sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            minWidth: 0,
            minHeight: 0,
            bgcolor: '#0f172a',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            boxShadow: '0 18px 36px rgba(2, 6, 23, 0.38)',
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              px: 2,
              py: 1.5,
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
              display: 'flex',
              flexDirection: 'column',
              gap: 1.25,
              bgcolor: '#111827',
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1.5}>
              <Stack spacing={0.5}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Typography sx={{ fontSize: 22, fontWeight: 700, color: '#f8fafc', lineHeight: 1.1 }}>
                    {activeSymbol || '선택된 심볼 없음'}
                  </Typography>
                </Stack>
                {latestCandle ? (
                  <Stack direction="row" spacing={1.25} flexWrap="wrap" sx={{ color: '#94a3b8' }}>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      시가 <Box component="span" sx={{ color: '#f8fafc', fontWeight: 600 }}>{formatChartPrice(latestCandle.open)}</Box>
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      고가 <Box component="span" sx={{ color: '#f87171', fontWeight: 600 }}>{formatChartPrice(latestCandle.high)}</Box>
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      저가 <Box component="span" sx={{ color: '#60a5fa', fontWeight: 600 }}>{formatChartPrice(latestCandle.low)}</Box>
                    </Typography>
                    <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                      종가 <Box component="span" sx={{ color: latestCandle.close >= latestCandle.open ? '#f87171' : '#60a5fa', fontWeight: 700 }}>{formatChartPrice(latestCandle.close)}</Box>
                    </Typography>
                  </Stack>
                ) : (
                  <Typography variant="caption" sx={{ color: '#94a3b8' }}>
                    전략 설정의 이동평균선을 차트에 반영하고, 거래량과 RSI, MACD를 항상 함께 표시합니다.
                  </Typography>
                )}
              </Stack>

              <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
                {chartTimeframeOptions.map((option, index) => (
                  <Stack key={option.value} direction="row" spacing={0.75} alignItems="center">
                    <Button
                      size="small"
                      variant="text"
                      disableRipple
                      onClick={() => setChartTimeframe(option.value)}
                      sx={{
                        minWidth: 0,
                        px: 0,
                        py: 0,
                        fontSize: 14,
                        fontWeight: 400,
                        lineHeight: 1,
                        color: chartTimeframe === option.value ? '#f8fafc' : '#94a3b8',
                        textTransform: 'none',
                        '&:hover': {
                          bgcolor: 'transparent',
                          color: '#f8fafc',
                        },
                      }}
                    >
                      {option.label}
                    </Button>
                    {index < chartTimeframeOptions.length - 1 ? (
                      <Typography sx={{ color: '#475569', fontSize: 13, lineHeight: 1 }}>/</Typography>
                    ) : null}
                  </Stack>
                ))}
                <Chip
                  label={chartOverlays.signalMarkers ? '신호 마커 표시' : '신호 마커 숨김'}
                  size="small"
                  onClick={() => toggleChartOverlay('signalMarkers')}
                  sx={{
                    height: 24,
                    fontSize: 11,
                    fontWeight: 500,
                    color: chartOverlays.signalMarkers ? '#f8fafc' : '#94a3b8',
                    bgcolor: chartOverlays.signalMarkers ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    cursor: 'pointer',
                  }}
                />
              </Stack>
            </Stack>

            <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
              {activeIndicatorSettings.movingAverages.map((movingAverage) => (
                <Chip
                  key={movingAverage.id}
                  label={`${movingAverage.type.toUpperCase()} ${movingAverage.length}`}
                  size="small"
                  sx={neutralIndicatorChipSx}
                />
              ))}
              <Chip
                label="거래량"
                size="small"
                sx={neutralIndicatorChipSx}
              />
              <Chip
                label={`RSI ${activeIndicatorSettings.rsi.length}`}
                size="small"
                sx={neutralIndicatorChipSx}
              />
              <Chip
                label={`MACD ${activeIndicatorSettings.macd.fastLength}, ${activeIndicatorSettings.macd.slowLength}, ${activeIndicatorSettings.macd.signalLength}`}
                size="small"
                sx={neutralIndicatorChipSx}
              />
            </Stack>
          </Box>

          <Box
            sx={{
              flexGrow: 1,
              minHeight: 0,
              display: 'flex',
              alignItems: 'stretch',
              justifyContent: 'center',
              position: 'relative',
              bgcolor: '#0b1120',
            }}
          >
            {!activeSymbol ? (
              <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                <Typography color="inherit">차트를 보려면 세션과 심볼을 선택하세요.</Typography>
              </Box>
            ) : chartData?.candles?.length ? (
              <CandlestickChart
                key={`${activeSymbol}-${chartTimeframe}-${session?.strategy_version_id ?? 'no-strategy'}`}
                data={chartData?.candles ?? []}
                indicatorSettings={activeIndicatorSettings}
                signals={activeSymbolSignals}
                showSignalMarkers={chartOverlays.signalMarkers}
                onMarkerSelect={(signalId) => {
                  setSelectedSignalId(signalId)
                  setBottomTab(1)
                }}
              />
            ) : (
              <Box sx={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Box sx={{ textAlign: 'center', color: '#94a3b8' }}>
                  <Activity size={32} color="#94a3b8" style={{ marginBottom: 8 }} />
                  <Typography color="inherit">차트 데이터를 기다리는 중입니다...</Typography>
                </Box>
              </Box>
            )}
          </Box>
        </Card>

        {/* Right Panel - Detail Tabs */}
        <Card sx={{ width: 440, display: 'flex', flexDirection: 'column', flexShrink: 0, minHeight: 0 }}>
          <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
            <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2}>
              <Typography variant="subtitle2" fontWeight={700}>
                세션 상세
              </Typography>
              <EventLogHelpPopover active={bottomTab === 0} />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {session
                ? `${activeSessionEntry?.strategyName ?? selectedStrategyGroup?.strategyName ?? '선택된 전략 없음'} · ${session.id.split('-')[0]}`
                : '선택된 세션 없음'}
            </Typography>
          </Box>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs
              value={bottomTab}
              onChange={(_, v) => setBottomTab(v)}
              variant="scrollable"
              scrollButtons="auto"
              allowScrollButtonsMobile
              sx={{ minHeight: 40 }}
            >
              <Tab label="이벤트 로그" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="전략 해설" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="신호" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="주문" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="리스크" sx={{ minHeight: 40, py: 1 }} />
            </Tabs>
          </Box>
          <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
            {bottomTab === 0 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>시간</TableCell>
                      <TableCell>레벨</TableCell>
                      <TableCell>채널</TableCell>
                      <TableCell>메시지</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!eventTimeline.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography color="text.secondary">이벤트 로그가 없습니다</Typography></TableCell></TableRow>
                    ) : (
                      eventTimeline.slice(0, 30).map((log) => (
                        <TableRow
                          key={`${log.channel}:${log.id}`}
                          ref={setEventLogRowRef(`${log.channel}:${log.id}`)}
                          hover
                          sx={{ '& td': { backgroundColor: 'transparent' } }}
                        >
                          <TableCell><Typography variant="caption" color="text.secondary">{formatTime(log.timestamp)}</Typography></TableCell>
                          <TableCell><Typography variant="caption">{translateLogLevel(String(log.level).toLowerCase())}</Typography></TableCell>
                          <TableCell><Typography variant="caption">{translateLogChannel(log.channel)}</Typography></TableCell>
                          <TableCell>
                            <Stack spacing={0.25}>
                              <Typography variant="caption">{log.message}</Typography>
                              <Typography variant="caption" color="text.secondary" fontFamily="monospace">
                                {log.event_type ?? '-'}
                              </Typography>
                            </Stack>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : null}

            {bottomTab === 1 ? (
              <StrategyExplainPanel
                signals={orderedSignals}
                selectedSignalId={selectedSignalId}
                onSelectSignal={setSelectedSignalId}
                strategyConfig={activeStrategyConfig}
              />
            ) : null}

            {bottomTab === 2 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>시간</TableCell>
                      <TableCell>심볼</TableCell>
                      <TableCell>액션</TableCell>
                      <TableCell align="right">가격</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!orderedSignals.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography color="text.secondary">신호가 없습니다</Typography></TableCell></TableRow>
                    ) : (
                      orderedSignals.map((signal) => {
                        const isSelected = signal.id === selectedSignalId
                        const isExplainBlocked = signal.blocked || Boolean(signal.explain_payload?.risk_blocks?.length)

                        return (
                        <TableRow
                          key={signal.id}
                          ref={setSignalRowRef(signal.id)}
                          hover
                          onClick={() => {
                            setSelectedSignalId(signal.id)
                            setBottomTab(1)
                          }}
                          sx={{
                            cursor: 'pointer',
                            bgcolor: isSelected
                              ? 'action.hover'
                              : (isExplainBlocked ? 'rgba(255, 152, 0, 0.05)' : 'transparent'),
                            '& td': { backgroundColor: 'transparent' },
                          }}
                        >
                          <TableCell><Typography variant="caption" color="text.secondary">{formatTime(signal.snapshot_time)}</Typography></TableCell>
                          <TableCell><Typography variant="caption" fontWeight={600}>{signal.symbol}</Typography></TableCell>
                          <TableCell>
                            <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
                              <StatusText tone={getActionTone(signal.action)}>{translateSignalAction(signal.action)}</StatusText>
                              {isExplainBlocked ? <StatusText tone="warning">차단</StatusText> : null}
                            </Stack>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              {signal.signal_price?.toLocaleString() ?? '-'}
                            </Typography>
                          </TableCell>
                        </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : null}

            {bottomTab === 3 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>시간</TableCell>
                      <TableCell>역할</TableCell>
                      <TableCell>상태</TableCell>
                      <TableCell align="right">수량</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!orders?.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography color="text.secondary">주문이 없습니다</Typography></TableCell></TableRow>
                    ) : (
                      orders.map((order) => (
                        <TableRow
                          key={order.id}
                          ref={setOrderRowRef(order.id)}
                          hover
                          sx={{ '& td': { backgroundColor: 'transparent' } }}
                        >
                          <TableCell><Typography variant="caption" color="text.secondary">{formatTime(order.submitted_at)}</Typography></TableCell>
                          <TableCell><Typography variant="caption">{translateOrderRole(order.order_role)}</Typography></TableCell>
                          <TableCell><Typography variant="caption">{translateOrderState(order.order_state)}</Typography></TableCell>
                          <TableCell align="right"><Typography variant="caption">{order.executed_qty}/{order.requested_qty}</Typography></TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : null}

            {bottomTab === 4 ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>시간</TableCell>
                      <TableCell>심각도</TableCell>
                      <TableCell>코드</TableCell>
                      <TableCell>메시지</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!riskEvents?.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography color="text.secondary">리스크 이벤트가 없습니다</Typography></TableCell></TableRow>
                    ) : (
                      riskEvents.map((event) => (
                        <TableRow
                          key={event.id}
                          ref={setRiskRowRef(event.id)}
                          hover
                          sx={{ '& td': { backgroundColor: 'transparent' } }}
                        >
                          <TableCell>
                            <Typography variant="caption" color="text.secondary">
                              {formatTime(event.created_at)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <StatusText tone={event.severity === 'WARN' ? 'warning' : 'danger'}>
                              {event.severity}
                            </StatusText>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" fontFamily="monospace">
                              {event.code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption">{event.message}</Typography>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : null}
          </Box>
        </Card>
      </Box>

    </Box>
  )
}
