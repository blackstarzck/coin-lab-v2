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
  FormControl,
  MenuItem,
  Select
} from '@mui/material'
import type { SelectChangeEvent } from '@mui/material/Select'
import { useQuery } from '@tanstack/react-query'
import { Activity, AlertTriangle, Info, StopCircle, RefreshCw } from 'lucide-react'
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
import { DetailGuidePopover, EVENT_LOG_GUIDE_SECTIONS, type GuideSection } from '@/features/monitoring/EventLogHelpPopover'
import { useStrategies } from '@/features/strategies/api'
import { useUiStore } from '@/stores/ui-store'
import { CandlestickChart } from '@/shared/charts/CandlestickChart'
import { useChartStream } from '@/features/monitoring/useChartStream'
import { useActiveSymbolPrices, type LiveSymbolPrice } from '@/features/monitoring/useActiveSymbolPrices'
import { StrategyExplainPanel } from '@/features/monitoring/StrategyExplainPanel'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useLogs } from '@/features/logs/api'
import {
  formatDateTime,
  formatTime,
  translateLogChannel,
  translateLogLevel,
  translateMode,
  translateOrderRole,
  translateOrderState,
  translateSessionStatus,
  translateSignalAction,
} from '@/shared/lib/i18n'
import { apiClient } from '@/shared/api/client'
import type { Order, RiskEvent, Signal } from '@/entities/session/types'
import type { StrategyVersion } from '@/entities/strategy/types'
import type { ApiResponse } from '@/shared/types/api'
import { resolveChartIndicatorSettings } from '@/shared/charts/chartIndicators'
import { IncrementalTableLoadMore } from '@/shared/ui/IncrementalTableLoadMore'
import { StatusText, type StatusTextTone } from '@/shared/ui/StatusText'
import { TwoLineDateTime } from '@/shared/ui/TwoLineDateTime'
import { useAnimatedTableRows } from '@/shared/ui/useAnimatedTableRows'
import { useIncrementalTableRows } from '@/shared/ui/useIncrementalTableRows'

const DETAIL_REFRESH_INTERVAL_MS = 2_000
const POSITION_REFRESH_INTERVAL_MS = 5_000
const SESSION_REFRESH_INTERVAL_MS = 5_000
const SESSION_LIST_REFRESH_INTERVAL_MS = 10_000
const SIGNAL_ORDER_MATCH_WINDOW_MS = 15 * 60 * 1000
const DETAIL_TABLE_PAGE_SIZE = 15
const GUIDE_OVERLAY_BG = 'rgba(7, 10, 18, 0.86)'

type SignalOrderTimelineRow = {
  id: string
  kind: 'signal' | 'order-only'
  sortAt: number
  signal?: Signal
  order?: Order
  riskEvent?: RiskEvent
}

type EntryRateLayout = 'stacked' | 'inline'
type EntryRateStage = 1 | 2 | 3 | 4

function toTimestamp(value: string | null | undefined): number {
  if (!value) {
    return 0
  }
  const parsed = new Date(value).getTime()
  return Number.isFinite(parsed) ? parsed : 0
}

function getOrderEventTime(order: Order): string | null {
  return order.submitted_at ?? order.filled_at ?? null
}

function getOrderTimestamp(order: Order): number {
  return toTimestamp(getOrderEventTime(order))
}

function getRiskTimestamp(event: RiskEvent): number {
  return toTimestamp(event.created_at)
}

function formatEntryRate(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) {
    return '-'
  }
  return `${Math.round(value)}%`
}

function getEntryRateStage(value: number | null | undefined): EntryRateStage | null {
  if (value == null || !Number.isFinite(value)) {
    return null
  }
  if (value < 25) {
    return 1
  }
  if (value < 50) {
    return 2
  }
  if (value < 75) {
    return 3
  }
  return 4
}

function formatEntryRateWindowLabel(windowSec: number | null | undefined): string {
  if (windowSec == null || windowSec <= 0) {
    return '최근 체결 기준'
  }
  if (windowSec % 60 === 0) {
    const minutes = windowSec / 60
    return `최근 ${minutes}분 체결 기준`
  }
  return `최근 ${windowSec}초 체결 기준`
}

function doesOrderMatchSignal(signal: Signal, order: Order): boolean {
  if (signal.symbol !== order.symbol) {
    return false
  }
  if (signal.action === 'ENTER') {
    return order.order_role === 'ENTRY'
  }
  return order.order_role !== 'ENTRY'
}

const SIGNAL_ORDER_GUIDE_SECTIONS: GuideSection[] = [
  {
    title: '신호 컬럼',
    items: [
      {
        label: '진입',
        description: 'ENTER 신호입니다. 전략 조건이 충족되어 새 진입을 시도한 경우입니다.',
      },
      {
        label: '청산',
        description: 'EXIT 신호입니다. 보유 포지션을 닫는 방향의 전략 판단입니다.',
      },
      {
        label: '차단',
        description: '신호는 생성됐지만 리스크 규칙이나 실행 조건 때문에 주문으로 이어지지 않은 경우 함께 표시됩니다.',
      },
      {
        label: '주문 단독',
        description: '연결 가능한 신호 없이 주문 기록만 남은 행입니다. 과거 데이터나 매칭 불가 케이스를 뜻합니다.',
      },
    ],
  },
  {
    title: '실행 결과 컬럼',
    items: [
      {
        label: '생성됨 / 제출됨 / 부분 체결',
        description: '주문이 생성되었거나, 제출되었거나, 일부만 체결된 상태입니다.',
      },
      {
        label: '체결 완료',
        description: '주문이 전부 체결된 상태이며, 아래 줄에는 주문 시간만 표시됩니다.',
      },
      {
        label: '취소됨 / 거부됨 / 만료됨 / 실패',
        description: '주문이 정상 체결로 끝나지 않은 상태입니다.',
      },
      {
        label: '리스크 차단',
        description: '리스크 규칙이 실행을 막은 상태입니다. 행의 i 아이콘 툴팁에서 코드와 메시지를 확인할 수 있습니다.',
      },
      {
        label: '실행 차단',
        description: '주문 생성 전 실행 단계에서 차단된 상태입니다. 자세한 사유는 i 아이콘 툴팁에 들어갑니다.',
      },
      {
        label: '주문 연결 없음',
        description: '신호는 기록됐지만 연결된 주문이나 차단 기록을 찾지 못한 상태입니다.',
      },
    ],
  },
]

function ExecutionResultHint({
  label,
  tone = 'default',
  tooltip,
}: {
  label: string
  tone?: StatusTextTone
  tooltip?: ReactNode
}) {
  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <StatusText tone={tone}>{label}</StatusText>
      {tooltip ? (
        <Tooltip
          arrow
          placement="top-start"
          title={tooltip}
          slotProps={{
            tooltip: {
              sx: {
                color: '#e7edf7',
                bgcolor: GUIDE_OVERLAY_BG,
                backgroundImage: 'none',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: '0 24px 48px rgba(0, 0, 0, 0.42)',
                backdropFilter: 'blur(18px)',
              },
            },
            arrow: {
              sx: {
                color: GUIDE_OVERLAY_BG,
              },
            },
          }}
        >
          <Box
            component="span"
            onClick={(event) => event.stopPropagation()}
            onMouseDown={(event) => event.stopPropagation()}
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              color: 'text.secondary',
              cursor: 'help',
            }}
          >
            <Info size={12} strokeWidth={2.1} />
          </Box>
        </Tooltip>
      ) : null}
    </Stack>
  )
}

function EntryRateIndicator({
  value,
  label,
  variant = 'table',
  showLabel = false,
}: {
  value: number | null | undefined
  label?: string
  variant?: 'table' | 'header'
  showLabel?: boolean
}) {
  const stage = getEntryRateStage(value)

  if (stage === null) {
    return (
      <Typography variant="caption" color="text.secondary" noWrap>
        대기
      </Typography>
    )
  }

  const stageText = `${formatEntryRate(value)}(${stage}단계)`
  const displayValue = showLabel && label ? `${label} ${stageText}` : stageText

  return (
    <Stack spacing={0.15} alignItems={variant === 'header' ? 'flex-start' : 'flex-end'}>
      <Typography
        variant={variant === 'header' ? 'body2' : 'caption'}
        fontWeight={700}
        noWrap
        sx={{
          color: variant === 'header' ? '#e2e8f0' : 'text.primary',
          lineHeight: 1.15,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {displayValue}
      </Typography>
    </Stack>
  )
}

function EntryRateSummary({
  price,
  layout = 'stacked',
  showWindowLabel = false,
}: {
  price?: LiveSymbolPrice | null
  layout?: EntryRateLayout
  showWindowLabel?: boolean
}) {
  const buyRate = price?.buy_entry_rate_pct ?? null
  const sellRate = price?.sell_entry_rate_pct ?? null
  const hasRates = buyRate != null && Number.isFinite(buyRate) && sellRate != null && Number.isFinite(sellRate)
  const windowLabel = formatEntryRateWindowLabel(price?.entry_rate_window_sec)

  if (!hasRates) {
    return (
      <Stack
        direction={layout === 'inline' ? 'row' : 'column'}
        spacing={layout === 'inline' ? 0.75 : 0.25}
        alignItems={layout === 'inline' ? 'center' : 'flex-start'}
      >
        {showWindowLabel ? (
          <Typography variant="caption" sx={{ color: '#94a3b8' }}>
            {windowLabel}
          </Typography>
        ) : null}
        <Typography variant="caption" color="text.secondary">
          진입률 데이터 대기
        </Typography>
      </Stack>
    )
  }

  return (
    <Stack
      direction={layout === 'inline' ? 'row' : 'column'}
      spacing={layout === 'inline' ? 0.9 : 0.2}
      alignItems={layout === 'inline' ? 'center' : 'flex-start'}
      flexWrap="wrap"
      useFlexGap={layout === 'inline'}
    >
      {showWindowLabel ? (
        <Typography variant="caption" sx={{ color: '#94a3b8' }}>
          {windowLabel}
        </Typography>
      ) : null}
      <EntryRateIndicator value={buyRate} label="매수" variant={layout === 'inline' ? 'header' : 'table'} showLabel />
      <EntryRateIndicator value={sellRate} label="매도" variant={layout === 'inline' ? 'header' : 'table'} showLabel />
    </Stack>
  )
}

function SessionSelectMeta({
  versionLabel,
  status,
  mode,
  executedAt,
}: {
  versionLabel: string
  status: string
  mode: string
  executedAt: string | null
}) {
  return (
    <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>
      <Box component="span">{versionLabel}</Box>
      <Box component="span" sx={{ mx: 0.45 }}>
        /
      </Box>
      <Box component="span" sx={{ color: status === 'RUNNING' ? 'primary.main' : 'text.secondary' }}>
        {translateSessionStatus(status)}
      </Box>
      <Box component="span" sx={{ mx: 0.45 }}>
        /
      </Box>
      <Box component="span">{translateMode(mode)}</Box>
      <Box component="span" sx={{ mx: 0.45 }}>
        /
      </Box>
      <Box component="span">{executedAt ? formatDateTime(executedAt) : '실행 전'}</Box>
    </Typography>
  )
}

export default function MonitoringPage() {
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)
  const [bottomTab, setBottomTab] = useState(0)
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null)
  const detailPanelRef = useRef<HTMLDivElement | null>(null)

  const shouldLoadEventLogs = bottomTab === 0
  const shouldLoadStrategyExplain = bottomTab === 1
  const shouldLoadSignalOrderFlow = bottomTab === 2
  const shouldLoadOrders = shouldLoadSignalOrderFlow
  const shouldLoadRiskEvents = bottomTab === 3 || shouldLoadSignalOrderFlow
  const shouldLoadSignalData = shouldLoadStrategyExplain || shouldLoadSignalOrderFlow

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
  const signalOrderRows = useMemo<SignalOrderTimelineRow[]>(() => {
    const signalsAsc = [...(signals ?? [])].sort((left, right) => {
      const timeCompare = toTimestamp(left.snapshot_time) - toTimestamp(right.snapshot_time)
      if (timeCompare !== 0) {
        return timeCompare
      }
      return left.id.localeCompare(right.id)
    })
    const ordersAsc = [...(orders ?? [])].sort((left, right) => {
      const timeCompare = getOrderTimestamp(left) - getOrderTimestamp(right)
      if (timeCompare !== 0) {
        return timeCompare
      }
      return left.id.localeCompare(right.id)
    })
    const riskEventsAsc = [...(riskEvents ?? [])].sort((left, right) => {
      const timeCompare = getRiskTimestamp(left) - getRiskTimestamp(right)
      if (timeCompare !== 0) {
        return timeCompare
      }
      return left.id.localeCompare(right.id)
    })
    const usedOrderIds = new Set<string>()
    const usedRiskEventIds = new Set<string>()
    const rows: SignalOrderTimelineRow[] = []

    signalsAsc.forEach((signal, index) => {
      const signalTimestamp = toTimestamp(signal.snapshot_time)
      const nextSignal = signalsAsc.slice(index + 1).find((candidate) => candidate.symbol === signal.symbol)
      const nextSignalTimestamp = nextSignal ? toTimestamp(nextSignal.snapshot_time) : Number.POSITIVE_INFINITY
      const upperBound = Math.min(nextSignalTimestamp, signalTimestamp + SIGNAL_ORDER_MATCH_WINDOW_MS)

      const matchedOrder = ordersAsc.find((order) => (
        !usedOrderIds.has(order.id)
        && doesOrderMatchSignal(signal, order)
        && getOrderTimestamp(order) >= signalTimestamp
        && getOrderTimestamp(order) <= upperBound
      ))
      if (matchedOrder) {
        usedOrderIds.add(matchedOrder.id)
      }

      const matchedRiskEvent = matchedOrder
        ? undefined
        : riskEventsAsc.find((event) => (
          !usedRiskEventIds.has(event.id)
          && event.symbol === signal.symbol
          && getRiskTimestamp(event) >= signalTimestamp
          && getRiskTimestamp(event) <= upperBound
        ))
      if (matchedRiskEvent) {
        usedRiskEventIds.add(matchedRiskEvent.id)
      }

      rows.push({
        id: `signal:${signal.id}`,
        kind: 'signal',
        sortAt: signalTimestamp,
        signal,
        order: matchedOrder,
        riskEvent: matchedRiskEvent,
      })
    })

    ordersAsc.forEach((order) => {
      if (usedOrderIds.has(order.id)) {
        return
      }
      rows.push({
        id: `order:${order.id}`,
        kind: 'order-only',
        sortAt: getOrderTimestamp(order),
        order,
      })
    })

    return rows.sort((left, right) => {
      const timeCompare = right.sortAt - left.sortAt
      if (timeCompare !== 0) {
        return timeCompare
      }
      return right.id.localeCompare(left.id)
    })
  }, [orders, riskEvents, signals])
  const eventLogTable = useIncrementalTableRows({
    items: eventTimeline,
    enabled: bottomTab === 0,
    pageSize: DETAIL_TABLE_PAGE_SIZE,
    resetKey: `${activeSessionId}:event-log`,
    rootRef: detailPanelRef,
  })
  const signalOrderTable = useIncrementalTableRows({
    items: signalOrderRows,
    enabled: bottomTab === 2,
    pageSize: DETAIL_TABLE_PAGE_SIZE,
    resetKey: `${activeSessionId}:signal-order`,
    rootRef: detailPanelRef,
  })
  const riskTable = useIncrementalTableRows({
    items: riskEvents ?? [],
    enabled: bottomTab === 3,
    pageSize: DETAIL_TABLE_PAGE_SIZE,
    resetKey: `${activeSessionId}:risk`,
    rootRef: detailPanelRef,
  })
  const eventLogRowIds = useMemo(
    () => eventLogTable.visibleItems.map((log) => `${log.channel}:${log.id}`),
    [eventLogTable.visibleItems],
  )
  const signalOrderRowIds = useMemo(
    () => signalOrderTable.visibleItems.map((row) => row.id),
    [signalOrderTable.visibleItems],
  )
  const riskRowIds = useMemo(
    () => riskTable.visibleItems.map((event) => event.id),
    [riskTable.visibleItems],
  )
  const { setRowRef: setEventLogRowRef } = useAnimatedTableRows(eventLogRowIds)
  const { setRowRef: setSignalOrderRowRef } = useAnimatedTableRows(signalOrderRowIds)
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
    if (bottomTab > 3) {
      setBottomTab(3)
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

  const getActionTone = (action: string): 'success' | 'danger' => {
    return action === 'ENTER' ? 'success' : 'danger'
  }

  const getOrderStateTone = (state: string): 'success' | 'warning' | 'danger' | 'info' | 'default' => {
    switch (state) {
      case 'FILLED':
        return 'success'
      case 'CREATED':
      case 'SUBMITTED':
      case 'PARTIALLY_FILLED':
        return 'info'
      case 'CANCELLED':
      case 'EXPIRED':
        return 'warning'
      case 'REJECTED':
      case 'FAILED':
        return 'danger'
      default:
        return 'default'
    }
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

  const asNumber = (value: unknown) => {
    const parsed = typeof value === 'number' ? value : Number(value)
    return Number.isFinite(parsed) ? parsed : 0
  }

  const formatPriceValue = (value: number | null | undefined) => {
    if (value == null || !Number.isFinite(value)) {
      return '-'
    }
    return Math.round(value).toLocaleString('ko-KR')
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

  const selectedSessionOption = useMemo(
    () => filteredSessionEntries.find((entry) => entry.session.id === activeSessionId) ?? filteredSessionEntries[0] ?? null,
    [activeSessionId, filteredSessionEntries],
  )

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
      const livePrice = pricesBySymbol[symbol]
      const latestPrice = livePrice?.price
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
        price: livePrice ?? null,
      }
    })
  }, [availableSymbols, positions, pricesBySymbol])

  const activeSymbolPrice = activeSymbol ? pricesBySymbol[activeSymbol] ?? null : null

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
          <Typography variant="h6">모니터링</Typography>
          
          <Stack direction="row" spacing={1}>
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
        <Box sx={{ width: 400, display: 'flex', flexDirection: 'column', gap: 2, flexShrink: 0, minHeight: 0 }}>
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
                            <Typography variant="body2" fontWeight={500} noWrap>
                              {group.strategyName}
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

          <Card sx={{ display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Typography variant="subtitle2" fontWeight={700}>
                세션
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {selectedStrategyGroup ? `${selectedStrategyGroup.strategyName}의 세션` : '전략을 먼저 선택하세요'}
              </Typography>
            </Box>
            <Box>
              {isLoadingSessions ? (
                <Stack spacing={1} sx={{ p: 2 }}>
                  <Skeleton variant="rounded" height={40} />
                  <Skeleton variant="rounded" height={28} />
                </Stack>
              ) : filteredSessionEntries.length === 0 ? (
                <Box sx={{ p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    선택한 전략의 세션이 없습니다
                  </Typography>
                </Box>
              ) : (
                <Stack spacing={1.5} sx={{ p: 2 }}>
                  <FormControl fullWidth size="small">
                    <Select
                      value={selectedSessionOption?.session.id ?? ''}
                      onChange={(event: SelectChangeEvent<string>) => handleSessionSelect(event.target.value)}
                      displayEmpty
                      renderValue={(value) => {
                        const currentEntry = filteredSessionEntries.find((entry) => entry.session.id === value) ?? null
                        if (!currentEntry) {
                          return <Typography color="text.secondary">세션 선택</Typography>
                        }

                        const executedAt = currentEntry.session.started_at ?? currentEntry.session.created_at ?? null
                        const versionLabel = currentEntry.versionNo
                          ? `v${currentEntry.versionNo}`
                          : `v${currentEntry.session.strategy_version_id.split('-')[0]}`

                        return (
                          <Stack spacing={0.2} sx={{ minWidth: 0 }}>
                            <Typography variant="body2" fontFamily="monospace" fontWeight={500} noWrap>
                              {currentEntry.session.id.split('-')[0]}
                            </Typography>
                            <SessionSelectMeta
                              versionLabel={versionLabel}
                              status={currentEntry.session.status}
                              mode={currentEntry.session.mode}
                              executedAt={executedAt}
                            />
                          </Stack>
                        )
                      }}
                      MenuProps={{
                        PaperProps: {
                          sx: {
                            maxHeight: 360,
                            mt: 0.75,
                            color: '#e7edf7',
                            bgcolor: GUIDE_OVERLAY_BG,
                            backgroundImage: 'none',
                            border: '1px solid rgba(255, 255, 255, 0.08)',
                            boxShadow: '0 24px 48px rgba(0, 0, 0, 0.42)',
                            backdropFilter: 'blur(18px)',
                          },
                        },
                        MenuListProps: {
                          sx: {
                            p: 0.75,
                          },
                        },
                      }}
                    >
                      {filteredSessionEntries.map((entry) => {
                        const currentSession = entry.session
                        const executedAt = currentSession.started_at ?? currentSession.created_at ?? null
                        const versionLabel = entry.versionNo ? `v${entry.versionNo}` : `v${currentSession.strategy_version_id.split('-')[0]}`

                        return (
                          <MenuItem
                            key={currentSession.id}
                            value={currentSession.id}
                            sx={{
                              borderRadius: 1.25,
                              alignItems: 'flex-start',
                              py: 1,
                              '&:hover': {
                                bgcolor: 'rgba(255, 255, 255, 0.05)',
                              },
                              '&.Mui-selected': {
                                bgcolor: 'rgba(34, 197, 94, 0.18)',
                              },
                              '&.Mui-selected:hover': {
                                bgcolor: 'rgba(34, 197, 94, 0.24)',
                              },
                            }}
                          >
                            <Stack spacing={0.25} sx={{ minWidth: 0 }}>
                              <Typography variant="body2" fontFamily="monospace" fontWeight={500} noWrap>
                                {currentSession.id.split('-')[0]}
                              </Typography>
                              <SessionSelectMeta
                                versionLabel={versionLabel}
                                status={currentSession.status}
                                mode={currentSession.mode}
                                executedAt={executedAt}
                              />
                            </Stack>
                          </MenuItem>
                        )
                      })}
                    </Select>
                  </FormControl>
                </Stack>
              )}
            </Box>
          </Card>

          <Card sx={{ minHeight: 220, maxHeight: 280, display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ px: 2, py: 1.5, borderBottom: 1, borderColor: 'divider' }}>
              <Stack direction="row" spacing={0.75} alignItems="center">
                <Typography variant="subtitle2" fontWeight={700}>
                  수익 현황
                </Typography>
                <Tooltip
                  title="초기 자금 100만원"
                  placement="top"
                  arrow
                  slotProps={{
                    tooltip: {
                      sx: {
                        color: '#e7edf7',
                        bgcolor: GUIDE_OVERLAY_BG,
                        backgroundImage: 'none',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        boxShadow: '0 24px 48px rgba(0, 0, 0, 0.42)',
                        backdropFilter: 'blur(18px)',
                      },
                    },
                    arrow: {
                      sx: {
                        color: GUIDE_OVERLAY_BG,
                      },
                    },
                  }}
                >
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
                        <TableCell align="right">매수</TableCell>
                        <TableCell align="right">매도</TableCell>
                        <TableCell align="right">수익률</TableCell>
                        <TableCell align="right">손익</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {!symbolPerformanceRows.length ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
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
                              <Box sx={{ display: 'inline-flex', justifyContent: 'flex-end', minWidth: 0 }}>
                                <EntryRateIndicator value={row.price?.buy_entry_rate_pct ?? null} />
                              </Box>
                            </TableCell>
                            <TableCell align="right">
                              <Box sx={{ display: 'inline-flex', justifyContent: 'flex-end', minWidth: 0 }}>
                                <EntryRateIndicator value={row.price?.sell_entry_rate_pct ?? null} />
                              </Box>
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
                {activeSymbol ? <EntryRateSummary price={activeSymbolPrice} layout="inline" showWindowLabel /> : null}
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
            <Typography variant="subtitle2" fontWeight={700}>
              세션 상세
            </Typography>
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
              <Tab label="신호·주문" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="리스크" sx={{ minHeight: 40, py: 1 }} />
            </Tabs>
          </Box>
          <Box ref={detailPanelRef} sx={{ flexGrow: 1, overflowY: 'auto' }}>
            {bottomTab === 0 ? (
              <Box>
                <DetailGuidePopover
                  summary="채널, 레벨, 이벤트 코드를 함께 보면 로그 의미를 빠르게 파악할 수 있습니다."
                  sections={EVENT_LOG_GUIDE_SECTIONS}
                  footnote="로그 코드는 버전에 따라 조금 달라질 수 있습니다. 해석할 때는 채널과 메시지도 함께 보세요."
                />
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
                        eventLogTable.visibleItems.map((log) => (
                          <TableRow
                            key={`${log.channel}:${log.id}`}
                            ref={setEventLogRowRef(`${log.channel}:${log.id}`)}
                            sx={{ '& td': { backgroundColor: 'transparent' } }}
                          >
                            <TableCell><TwoLineDateTime value={log.timestamp} /></TableCell>
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
                <IncrementalTableLoadMore
                  batchSize={DETAIL_TABLE_PAGE_SIZE}
                  visibleCount={eventLogTable.visibleCount}
                  totalCount={eventLogTable.totalCount}
                  sentinelRef={eventLogTable.sentinelRef}
                />
              </Box>
            ) : null}

            {bottomTab === 1 ? (
              <StrategyExplainPanel
                signals={orderedSignals}
                selectedSignalId={selectedSignalId}
                onSelectSignal={setSelectedSignalId}
                strategyConfig={activeStrategyConfig}
                scrollRootRef={detailPanelRef}
                tablePageSize={DETAIL_TABLE_PAGE_SIZE}
              />
            ) : null}

            {bottomTab === 2 ? (
              <Box>
                <DetailGuidePopover
                  summary="신호 컬럼과 실행 결과 컬럼에 들어갈 수 있는 값들을 눌러서 확인할 수 있습니다."
                  sections={SIGNAL_ORDER_GUIDE_SECTIONS}
                  footnote="차단 계열 값은 행의 i 아이콘 툴팁에서 상세 코드나 메시지를 볼 수 있습니다."
                />
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                        <TableCell>시간</TableCell>
                        <TableCell>심볼</TableCell>
                        <TableCell>신호</TableCell>
                        <TableCell>실행 결과</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {!signalOrderRows.length ? (
                        <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography color="text.secondary">신호와 주문이 없습니다</Typography></TableCell></TableRow>
                      ) : (
                        signalOrderTable.visibleItems.map((row) => {
                          if (row.kind === 'order-only' && row.order) {
                            const orderTime = getOrderEventTime(row.order)
                            return (
                              <TableRow
                                key={row.id}
                                ref={setSignalOrderRowRef(row.id)}
                                sx={{ '& td': { backgroundColor: 'transparent' } }}
                              >
                                <TableCell>
                                  <TwoLineDateTime value={orderTime} />
                                </TableCell>
                                <TableCell><Typography variant="caption" fontWeight={600}>{row.order.symbol}</Typography></TableCell>
                                <TableCell>
                                  <Stack spacing={0.25}>
                                    <StatusText tone="info">주문 단독</StatusText>
                                    <Typography variant="caption" color="text.secondary">
                                      {translateOrderRole(row.order.order_role)}
                                    </Typography>
                                  </Stack>
                                </TableCell>
                                <TableCell>
                                  <Stack spacing={0.25}>
                                    <StatusText tone={getOrderStateTone(row.order.order_state)}>
                                      {translateOrderState(row.order.order_state)}
                                    </StatusText>
                                    {orderTime ? <Typography variant="caption" color="text.secondary">{formatTime(orderTime)}</Typography> : null}
                                  </Stack>
                                </TableCell>
                              </TableRow>
                            )
                          }

                          if (!row.signal) {
                            return null
                          }

                          const signal = row.signal
                          const explainRiskBlocks = Array.isArray(signal.explain_payload?.risk_blocks)
                            ? signal.explain_payload.risk_blocks
                            : []
                          const isBlocked = signal.blocked || explainRiskBlocks.length > 0 || Boolean(row.riskEvent)

                          return (
                            <TableRow
                              key={row.id}
                              ref={setSignalOrderRowRef(row.id)}
                              sx={{ '& td': { backgroundColor: 'transparent' } }}
                            >
                              <TableCell><TwoLineDateTime value={signal.snapshot_time} /></TableCell>
                              <TableCell><Typography variant="caption" fontWeight={600}>{signal.symbol}</Typography></TableCell>
                              <TableCell>
                                <Stack spacing={0.25}>
                                  <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
                                    <StatusText tone={getActionTone(signal.action)}>{translateSignalAction(signal.action)}</StatusText>
                                    {isBlocked ? <StatusText tone="warning">차단</StatusText> : null}
                                  </Stack>
                                  <Typography variant="caption" color="text.secondary" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                                    {formatPriceValue(signal.signal_price)}
                                  </Typography>
                                </Stack>
                              </TableCell>
                              <TableCell>
                                {row.order ? (
                                  <Stack spacing={0.25}>
                                    <StatusText tone={getOrderStateTone(row.order.order_state)}>
                                      {translateOrderState(row.order.order_state)}
                                    </StatusText>
                                    {getOrderEventTime(row.order) ? (
                                      <Typography variant="caption" color="text.secondary">
                                        {formatTime(getOrderEventTime(row.order) as string)}
                                      </Typography>
                                    ) : null}
                                  </Stack>
                                ) : row.riskEvent ? (
                                  <ExecutionResultHint
                                    label="리스크 차단"
                                    tone="warning"
                                    tooltip={(
                                      <Stack spacing={0.5}>
                                        <Typography variant="caption" sx={{ color: '#f8fafc', fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace' }}>
                                          {row.riskEvent.code}
                                        </Typography>
                                        <Typography variant="caption" sx={{ color: 'rgba(226, 232, 240, 0.88)' }}>
                                          {row.riskEvent.message}
                                        </Typography>
                                      </Stack>
                                    )}
                                  />
                                ) : explainRiskBlocks.length ? (
                                  <ExecutionResultHint
                                    label="실행 차단"
                                    tone="warning"
                                    tooltip={(
                                      <Stack spacing={0.5}>
                                        <Typography variant="caption" sx={{ color: 'rgba(226, 232, 240, 0.88)' }}>
                                          차단 코드
                                        </Typography>
                                        <Typography variant="caption" sx={{ color: '#f8fafc', fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace' }}>
                                          {explainRiskBlocks.join(', ')}
                                        </Typography>
                                      </Stack>
                                    )}
                                  />
                                ) : (
                                  <ExecutionResultHint
                                    label="주문 연결 없음"
                                    tooltip={(
                                      <Typography variant="caption" sx={{ color: 'rgba(226, 232, 240, 0.88)' }}>
                                        신호는 기록됐지만 연결된 주문이나 차단 기록을 찾지 못했습니다.
                                      </Typography>
                                    )}
                                  />
                                )}
                              </TableCell>
                            </TableRow>
                          )
                        })
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
                <IncrementalTableLoadMore
                  batchSize={DETAIL_TABLE_PAGE_SIZE}
                  visibleCount={signalOrderTable.visibleCount}
                  totalCount={signalOrderTable.totalCount}
                  sentinelRef={signalOrderTable.sentinelRef}
                />
              </Box>
            ) : null}

            {bottomTab === 3 ? (
              <Box>
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
                        riskTable.visibleItems.map((event) => (
                          <TableRow
                            key={event.id}
                            ref={setRiskRowRef(event.id)}
                            sx={{ '& td': { backgroundColor: 'transparent' } }}
                          >
                            <TableCell>
                              <TwoLineDateTime value={event.created_at} />
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
                <IncrementalTableLoadMore
                  batchSize={DETAIL_TABLE_PAGE_SIZE}
                  visibleCount={riskTable.visibleCount}
                  totalCount={riskTable.totalCount}
                  sentinelRef={riskTable.sentinelRef}
                />
              </Box>
            ) : null}
          </Box>
        </Card>
      </Box>

    </Box>
  )
}
