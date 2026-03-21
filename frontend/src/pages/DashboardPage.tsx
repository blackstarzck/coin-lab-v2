import { useNavigate } from 'react-router-dom'
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import type { Theme } from '@mui/material/styles'
import {
  Activity,
  ArrowUpRight,
  ChevronDown,
  Crosshair,
  Layers3,
  Radio,
  Wallet,
} from 'lucide-react'

import { useMonitoringSummary } from '@/features/monitoring/api'
import { useActiveSymbolPrices, type LiveSymbolPrice } from '@/features/monitoring/useActiveSymbolPrices'
import { useMonitoringSummaryStream } from '@/features/monitoring/useMonitoringSummaryStream'
import { formatKRW } from '@/shared/lib/format'
import {
  formatDateTime,
  formatRelativeTime,
  translateOrderRole,
  translateSeverity,
  translateStrategyType,
} from '@/shared/lib/i18n'
import { LabEmptyState } from '@/shared/ui/LabEmptyState'
import { LabMetricTile } from '@/shared/ui/LabMetricTile'
import { LabPageHeader } from '@/shared/ui/LabPageHeader'
import { LabSurfaceCard } from '@/shared/ui/LabSurfaceCard'

export default function DashboardPage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const { data: summary, isLoading } = useMonitoringSummary()
  const { isConnected } = useMonitoringSummaryStream()
  const dashboard = summary?.dashboard
  const trackedSymbols = Array.from(
    new Set((dashboard?.strategy_details ?? []).flatMap((item) => item.tracked_symbols)),
  )
  const { pricesBySymbol } = useActiveSymbolPrices(trackedSymbols)

  if (isLoading && summary === undefined) {
    return <DashboardSkeleton />
  }

  return (
    <Box sx={{ mx: 'auto', width: '100%', maxWidth: 1440, pb: 5 }}>
      <Stack spacing={3}>
        <LabPageHeader
          eyebrow="COIN LAB DASHBOARD"
          title="전략 실험 대시보드"
          description="전략 실험실의 현재 상태를 실시간으로 모니터링하고, 전략과 세션 성과를 같은 문맥에서 읽을 수 있도록 구성했습니다."
          actions={(
            <>
              <Chip
                icon={<Radio size={14} />}
                label={isConnected ? 'WebSocket Connected' : 'Reconnecting'}
                sx={pillSx(isConnected ? theme.palette.status.success : theme.palette.status.warning)}
              />
              <Button variant="contained" endIcon={<ArrowUpRight size={16} />} onClick={() => navigate('/monitoring')}>
                모니터링 열기
              </Button>
            </>
          )}
        />

        <LabSurfaceCard
          dataTestId="dashboard-hero"
          variant="glass"
          title={dashboard?.hero.title ?? 'Strategy Arena'}
          subtitle={dashboard?.hero.subtitle ?? '전략 실험실의 전체 컨텍스트를 한눈에 추적합니다.'}
          action={
            dashboard?.hero.latest_event_at ? (
              <Chip
                label={`최근 이벤트 ${formatRelativeTime(dashboard.hero.latest_event_at)}`}
                sx={pillNeutralSx(theme)}
              />
            ) : null
          }
        >
          <Stack spacing={2.5}>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {(dashboard?.strategy_strip ?? []).slice(0, 6).map((item) => (
                <Chip
                  key={item.strategy_id}
                  label={`${item.label} · ${formatSignedPercent(item.return_pct)}`}
                  onClick={() => navigate(`/strategies/${item.strategy_id}`)}
                  clickable
                  sx={pillSx(item.tone === 'danger' ? theme.palette.status.danger : theme.palette.status.success)}
                />
              ))}
            </Stack>

            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {(dashboard?.market_strip ?? []).map((item) => (
                <Chip
                  key={item.symbol}
                  label={item.symbol}
                  sx={{
                    ...pillNeutralSx(theme),
                    borderColor: item.risk_blocked
                      ? alpha(theme.palette.status.warning, 0.22)
                      : item.is_active
                        ? alpha(theme.palette.primary.main, 0.18)
                        : theme.palette.border.soft,
                    color: item.risk_blocked
                      ? theme.palette.status.warning
                      : item.is_active
                        ? theme.palette.primary.main
                        : theme.palette.text.secondary,
                  }}
                />
              ))}
            </Stack>

            <Box
              sx={{
                display: 'grid',
                gap: 2,
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(2, minmax(0, 1fr))',
                  xl: 'repeat(4, minmax(0, 1fr))',
                },
              }}
            >
              <Box>
                <LabMetricTile
                  icon={<Layers3 size={18} />}
                  label="활성 전략"
                  value={String(dashboard?.hero.active_strategy_count ?? 0)}
                  hint={dashboard?.hero.headline_strategy_name ?? '상위 전략 없음'}
                />
              </Box>
              <Box>
                <LabMetricTile
                  icon={<Activity size={18} />}
                  label="실행 중 세션"
                  value={String(dashboard?.hero.running_session_count ?? summary?.status_bar.running_session_count ?? 0)}
                  hint={`모의 ${summary?.status_bar.paper_session_count ?? 0} / 실전 ${summary?.status_bar.live_session_count ?? 0}`}
                />
              </Box>
              <Box>
                <LabMetricTile
                  icon={<Crosshair size={18} />}
                  label="활성 심볼"
                  value={String(dashboard?.hero.active_symbol_count ?? summary?.status_bar.active_symbol_count ?? 0)}
                  hint={`최근 신호 ${summary?.universe_summary.with_recent_signal_count ?? 0}개`}
                />
              </Box>
              <Box>
                <LabMetricTile
                  icon={<Wallet size={18} />}
                  label="최근 체결"
                  value={String(dashboard?.hero.recent_trade_count ?? 0)}
                  hint={`리스크 알림 ${summary?.risk_overview.active_alert_count ?? 0}건`}
                />
              </Box>
            </Box>
          </Stack>
        </LabSurfaceCard>

        <Box
          sx={{
            display: 'grid',
            gap: 2.5,
            alignItems: 'stretch',
            gridTemplateColumns: {
              xs: '1fr',
              xl: 'minmax(0, 1.9fr) minmax(320px, 0.9fr)',
            },
          }}
        >
          <Box>
            <LabSurfaceCard
              dataTestId="dashboard-performance-history"
              title="Performance History"
              subtitle="전략별 최근 성과 흐름을 체결 기준으로 정리했습니다."
            >
              <PerformanceHistorySection series={dashboard?.performance_history.series ?? []} />
            </LabSurfaceCard>
          </Box>

          <Box>
            <LabSurfaceCard
              dataTestId="dashboard-live-activity"
              title="Live Activity"
              subtitle="신호, 체결, 리스크 이벤트를 하나의 피드로 묶었습니다."
            >
              <LiveActivitySection items={dashboard?.live_activity ?? []} />
            </LabSurfaceCard>
          </Box>
        </Box>

        <LabSurfaceCard
          dataTestId="dashboard-trades"
          title="Last 50 Trades"
          subtitle="전략이 발생시킨 최근 체결 로그입니다."
        >
          <RecentTradesSection rows={dashboard?.recent_trades ?? []} />
        </LabSurfaceCard>

        <LabSurfaceCard
          dataTestId="dashboard-leaderboard"
          title="Leaderboard"
          subtitle="전략별 수익, 승률, 거래 수를 한 번에 비교합니다."
        >
          <LeaderboardSection rows={dashboard?.leaderboard ?? []} />
        </LabSurfaceCard>

        <LabSurfaceCard
          dataTestId="dashboard-strategy-grid"
          title="Strategy Details"
          subtitle="첨부 이미지의 모델 카드 영역을 전략 카드로 재해석했습니다."
        >
          <Box
            sx={{
              display: 'grid',
              gap: 2,
              gridTemplateColumns: {
                xs: '1fr',
                md: 'repeat(2, minmax(0, 1fr))',
                xl: 'repeat(3, minmax(0, 1fr))',
              },
              alignItems: 'stretch',
            }}
          >
            {(dashboard?.strategy_details ?? []).map((item) => (
              <Box key={item.strategy_id}>
                <StrategyDetailCard
                  strategy={item}
                  pricesBySymbol={pricesBySymbol}
                  onOpen={() => navigate(`/strategies/${item.strategy_id}`)}
                />
              </Box>
            ))}
          </Box>
        </LabSurfaceCard>

        <LabSurfaceCard
          dataTestId="dashboard-market-details"
          title="Market Details"
          subtitle="실험 후보군을 심볼 단위로 요약합니다."
        >
          <MarketDetailsSection rows={dashboard?.market_details ?? []} />
        </LabSurfaceCard>
      </Stack>
    </Box>
  )
}

function DashboardSkeleton() {
  return (
    <Box sx={{ mx: 'auto', width: '100%', maxWidth: 1520 }}>
      <Stack spacing={3}>
        <Skeleton variant="rounded" height={180} />
        <Grid container spacing={3}>
          <Grid item xs={12} xl={8}>
            <Skeleton variant="rounded" height={420} />
          </Grid>
          <Grid item xs={12} xl={4}>
            <Skeleton variant="rounded" height={420} />
          </Grid>
        </Grid>
        <Skeleton variant="rounded" height={320} />
        <Skeleton variant="rounded" height={320} />
        <Skeleton variant="rounded" height={520} />
        <Skeleton variant="rounded" height={420} />
      </Stack>
    </Box>
  )
}

function PerformanceHistorySection({
  series,
}: {
  series: {
    strategy_id: string
    strategy_name: string
    color: string
    return_pct: number
    points: { label: string; timestamp: string | null; value: number }[]
  }[]
}) {
  if (series.length === 0) {
    return <LabEmptyState message="전략별 성과 히스토리가 아직 없습니다." />
  }

  return (
    <Stack spacing={2.5}>
      <StrategyPerformanceChart series={series} />

      <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
        {series.map((item) => (
          <Box
            key={item.strategy_id}
            sx={{
              minWidth: 180,
              flex: '1 1 180px',
              minHeight: 84,
              borderRadius: '16px',
              border: `1px solid ${alpha(item.color, 0.12)}`,
              backgroundColor: alpha(item.color, 0.032),
              p: 1.5,
            }}
          >
            <Stack direction="row" justifyContent="space-between" spacing={1}>
              <Typography variant="body2" fontWeight={600}>
                {item.strategy_name}
              </Typography>
              <Typography variant="body2" sx={{ color: item.color, fontVariantNumeric: 'tabular-nums' }}>
                {formatSignedPercent(item.return_pct)}
              </Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {item.points[item.points.length - 1]?.label ?? '현재'} 기준
            </Typography>
          </Box>
        ))}
      </Stack>

      <Grid container spacing={2}>
        {series.slice(0, 3).map((item) => (
          <Grid item xs={12} md={4} key={`summary-${item.strategy_id}`}>
            <Typography variant="caption" color="text.secondary">
              주요 전략
            </Typography>
            <Typography variant="body1" sx={{ mt: 0.5 }}>
              {item.strategy_name}
            </Typography>
            <Typography variant="h6" sx={{ mt: 0.5, color: item.color }}>
              {formatSignedPercent(item.return_pct)}
            </Typography>
          </Grid>
        ))}
      </Grid>
    </Stack>
  )
}

function StrategyPerformanceChart({
  series,
}: {
  series: {
    strategy_id: string
    strategy_name: string
    color: string
    return_pct: number
    points: { label: string; timestamp: string | null; value: number }[]
  }[]
}) {
  const theme = useTheme()
  const viewBoxWidth = 960
  const viewBoxHeight = 360
  const padding = { top: 20, right: 24, bottom: 42, left: 52 }
  const chartWidth = viewBoxWidth - padding.left - padding.right
  const chartHeight = viewBoxHeight - padding.top - padding.bottom
  const values = series.flatMap((item) => item.points.map((point) => point.value))
  let minValue = Math.min(...values, 0)
  let maxValue = Math.max(...values, 0)
  if (minValue === maxValue) {
    minValue -= 1
    maxValue += 1
  }
  const normalizeY = (value: number) => {
    const ratio = (value - minValue) / (maxValue - minValue)
    return padding.top + chartHeight - ratio * chartHeight
  }

  const longestSeries = series.reduce((candidate, current) => (current.points.length > candidate.points.length ? current : candidate), series[0])

  return (
    <Box
      sx={{
        width: '100%',
        borderRadius: '20px',
        border: `1px solid ${theme.palette.border.soft}`,
        background:
          `radial-gradient(circle at top right, ${alpha(theme.palette.primary.main, 0.024)} 0%, transparent 34%), ` +
          `linear-gradient(180deg, ${alpha(theme.palette.common.white, 0.012)} 0%, ${alpha(theme.palette.common.white, 0.008)} 100%)`,
        p: 2,
      }}
    >
      <Box component="svg" viewBox={`0 0 ${viewBoxWidth} ${viewBoxHeight}`} sx={{ width: '100%', height: 'auto', display: 'block' }}>
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const value = maxValue - (maxValue - minValue) * ratio
          const y = padding.top + chartHeight * ratio
          return (
            <g key={ratio}>
              <line
                x1={padding.left}
                y1={y}
                x2={padding.left + chartWidth}
                y2={y}
                stroke={alpha(theme.palette.common.white, 0.05)}
                strokeDasharray="6 8"
              />
              <text
                x={padding.left - 10}
                y={y + 4}
                fill={theme.palette.text.secondary}
                fontSize="12"
                textAnchor="end"
              >
                {value.toFixed(0)}%
              </text>
            </g>
          )
        })}

        {longestSeries.points.map((point, index) => {
          const x =
            padding.left +
            (index / Math.max(longestSeries.points.length - 1, 1)) * chartWidth
          return (
            <text
              key={`${point.label}-${index}`}
              x={x}
              y={viewBoxHeight - 12}
              fill={theme.palette.text.secondary}
              fontSize="12"
              textAnchor={index === 0 ? 'start' : index === longestSeries.points.length - 1 ? 'end' : 'middle'}
            >
              {point.label}
            </text>
          )
        })}

        {series.map((item) => {
          const coords = item.points.map((point, index) => {
            const x = padding.left + (index / Math.max(item.points.length - 1, 1)) * chartWidth
            const y = normalizeY(point.value)
            return { x, y, point }
          })
          const path = coords
            .map((coord, index) => `${index === 0 ? 'M' : 'L'} ${coord.x.toFixed(2)} ${coord.y.toFixed(2)}`)
            .join(' ')

          return (
            <g key={item.strategy_id}>
              <path
                d={path}
                fill="none"
                stroke={item.color}
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              {coords.map((coord, index) => (
                <circle
                  key={`${item.strategy_id}-${index}`}
                  cx={coord.x}
                  cy={coord.y}
                  r="4"
                  fill={item.color}
                  stroke={theme.palette.background.paper}
                  strokeWidth="2"
                />
              ))}
            </g>
          )
        })}
      </Box>
    </Box>
  )
}

function LiveActivitySection({
  items,
}: {
  items: {
    id: string
    kind: string
    strategy_name: string
    symbol: string | null
    title: string
    detail: string
    occurred_at: string
    tone: string
  }[]
}) {
  const theme = useTheme()

  if (items.length === 0) {
    return <LabEmptyState message="실시간 활동이 아직 없습니다." />
  }

  return (
    <Stack spacing={1.5}>
      {items.map((item) => (
        <Box
          key={item.id}
          sx={{
            borderRadius: '18px',
            border: `1px solid ${theme.palette.border.soft}`,
            backgroundColor: alpha(theme.palette.common.white, 0.008),
            p: 1.5,
          }}
        >
          <Stack direction="row" spacing={1.25} alignItems="flex-start">
            <Box
              sx={{
                mt: 0.35,
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: toneColor(theme, item.tone),
                boxShadow: `0 0 0 4px ${alpha(toneColor(theme, item.tone), 0.12)}`,
              }}
            />
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Stack direction="row" justifyContent="space-between" spacing={1}>
                <Typography variant="body2" fontWeight={600} noWrap>
                  {item.title}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                  {formatRelativeTime(item.occurred_at)}
                </Typography>
              </Stack>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {item.strategy_name}
                {item.symbol ? ` · ${item.symbol}` : ''} · {item.detail}
              </Typography>
            </Box>
          </Stack>
        </Box>
      ))}
    </Stack>
  )
}

function RecentTradesSection({
  rows,
}: {
  rows: {
    id: string
    strategy_name: string
    symbol: string
    order_role: string
    price: number
    qty: number
    filled_at: string
  }[]
}) {
  if (rows.length === 0) {
    return <LabEmptyState message="최근 체결 내역이 없습니다." />
  }

  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
            <TableCell>전략</TableCell>
            <TableCell>체결</TableCell>
            <TableCell>심볼</TableCell>
            <TableCell align="right">수량</TableCell>
            <TableCell align="right">가격</TableCell>
            <TableCell align="right">시간</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.slice(0, 12).map((row) => (
            <TableRow key={row.id} hover>
              <TableCell>
                <Typography variant="body2" fontWeight={600}>
                  {row.strategy_name}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color={row.order_role === 'ENTRY' ? 'status.success' : 'info.main'}>
                  {translateOrderRole(row.order_role)}
                </Typography>
              </TableCell>
              <TableCell>{row.symbol}</TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {formatQuantity(row.qty)}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {formatKRW(row.price)}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {formatDateTime(row.filled_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function LeaderboardSection({
  rows,
}: {
  rows: {
    strategy_id: string
    strategy_name: string
    strategy_type: string
    active_session_count: number
    account_value: number
    realized_pnl: number
    unrealized_pnl: number
    return_pct: number
    win_rate_pct: number | null
    trades: number
    risk_alert_count: number
  }[]
}) {
  if (rows.length === 0) {
    return <LabEmptyState message="비교할 전략 데이터가 없습니다." />
  }

  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
            <TableCell>순위</TableCell>
            <TableCell>전략</TableCell>
            <TableCell align="right">세션</TableCell>
            <TableCell align="right">계정 가치</TableCell>
            <TableCell align="right">실현/평가</TableCell>
            <TableCell align="right">수익률</TableCell>
            <TableCell align="right">승률</TableCell>
            <TableCell align="right">거래 수</TableCell>
            <TableCell align="right">리스크</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={row.strategy_id} hover>
              <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>{index + 1}</TableCell>
              <TableCell>
                <Typography variant="body2" fontWeight={600}>
                  {row.strategy_name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {translateStrategyType(row.strategy_type)}
                </Typography>
              </TableCell>
              <TableCell align="right">{row.active_session_count}</TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {formatCompactKRW(row.account_value)}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                <Stack alignItems="flex-end" spacing={0.2}>
                  <Typography variant="body2" color={row.realized_pnl >= 0 ? 'status.success' : 'status.danger'}>
                    {formatSignedKRW(row.realized_pnl)}
                  </Typography>
                  <Typography variant="caption" color={row.unrealized_pnl >= 0 ? 'status.success' : 'status.danger'}>
                    {formatSignedKRW(row.unrealized_pnl)}
                  </Typography>
                </Stack>
              </TableCell>
              <TableCell align="right" sx={{ color: row.return_pct >= 0 ? 'status.success' : 'status.danger', fontVariantNumeric: 'tabular-nums' }}>
                {formatSignedPercent(row.return_pct)}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {row.win_rate_pct === null ? '-' : `${row.win_rate_pct.toFixed(1)}%`}
              </TableCell>
              <TableCell align="right">{row.trades}</TableCell>
              <TableCell align="right">{row.risk_alert_count}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function StrategyDetailCard({
  strategy,
  pricesBySymbol,
  onOpen,
}: {
  strategy: {
    strategy_id: string
    strategy_name: string
    strategy_type: string
    active_session_count: number
    account_value: number
    realized_pnl: number
    unrealized_pnl: number
    return_pct: number
    win_rate_pct: number | null
    trades: number
    risk_alert_count: number
    paper_session_count: number
    live_session_count: number
    active_position_count: number
    degraded_session_count: number
    monitoring_state: 'idle' | 'running' | 'degraded' | string
    tracked_symbols: string[]
    last_signal_at: string | null
    description: string | null
    open_positions: {
      symbol: string
      side: string
      quantity: number
      avg_entry_price: number | null
      unrealized_pnl_pct: number
    }[]
  }
  pricesBySymbol: Record<string, LiveSymbolPrice>
  onOpen: () => void
}) {
  const theme = useTheme()
  const entryRates = aggregateEntryRates(strategy.tracked_symbols, pricesBySymbol)

  return (
    <Card
      sx={{
        height: '100%',
        borderRadius: '18px',
        border: `1px solid ${theme.palette.border.soft}`,
        backgroundColor: alpha(theme.palette.common.white, 0.008),
      }}
    >
      <CardContent sx={{ p: 2.25, height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Stack sx={{ height: '100%' }}>
          <Stack direction="row" justifyContent="space-between" spacing={1.5} sx={{ mb: 1.75 }}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="h6">{strategy.strategy_name}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.4 }}>
                {translateStrategyType(strategy.strategy_type)}
              </Typography>
            </Box>
            <Button
              variant="text"
              onClick={onOpen}
              sx={{ minWidth: 0, color: 'primary.main', alignSelf: 'flex-start' }}
            >
              열기
            </Button>
          </Stack>

          <Box sx={{ minHeight: 42, mb: 2 }}>
            {strategy.description ? (
              <Typography variant="body2" color="text.secondary">
                {strategy.description}
              </Typography>
            ) : null}
          </Box>

          <Grid container spacing={1.5} sx={{ mb: 2 }}>
          <Grid item xs={6}>
            <MiniMetric label="계정 가치" value={formatCompactKRW(strategy.account_value)} tone="neutral" />
          </Grid>
          <Grid item xs={6}>
            <MiniMetric label="총 수익률" value={formatSignedPercent(strategy.return_pct)} tone={strategy.return_pct >= 0 ? 'positive' : 'negative'} />
          </Grid>
          <Grid item xs={6}>
            <MiniMetric label="실현 손익" value={formatSignedKRW(strategy.realized_pnl)} tone={strategy.realized_pnl >= 0 ? 'positive' : 'negative'} />
          </Grid>
          <Grid item xs={6}>
            <MiniMetric label="승률" value={strategy.win_rate_pct === null ? '-' : `${strategy.win_rate_pct.toFixed(1)}%`} tone="neutral" />
          </Grid>
          </Grid>

          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1, mb: 2 }}>
            <Chip label={monitoringStateLabel(strategy.monitoring_state)} sx={monitoringStateChipSx(theme, strategy.monitoring_state)} />
            <Chip label={`세션 ${strategy.active_session_count}`} sx={pillNeutralSx(theme)} />
            <Chip label={`모의 ${strategy.paper_session_count}`} sx={pillNeutralSx(theme)} />
            <Chip label={`실전 ${strategy.live_session_count}`} sx={pillNeutralSx(theme)} />
            <Chip label={`포지션 ${strategy.active_position_count}`} sx={pillNeutralSx(theme)} />
            {strategy.degraded_session_count > 0 ? (
              <Chip label={`지연 ${strategy.degraded_session_count}`} sx={pillSx(theme.palette.status.warning)} />
            ) : null}
          </Stack>

          <Typography variant="caption" color="text.secondary">
            추적 심볼
          </Typography>
          <Stack direction="row" spacing={0.75} sx={{ flexWrap: 'wrap', gap: 0.75, mt: 0.75, mb: 2, minHeight: 36 }}>
            {strategy.tracked_symbols.length === 0 ? (
              <Chip label="심볼 없음" size="small" sx={pillNeutralSx(theme)} />
            ) : (
              strategy.tracked_symbols.map((symbol) => (
                <Chip key={symbol} label={symbol} size="small" sx={pillNeutralSx(theme)} />
              ))
            )}
          </Stack>

          <Typography variant="caption" color="text.secondary">
            실시간 진입률
          </Typography>
          <Grid container spacing={1.5} sx={{ mt: 0.75, mb: 2 }}>
            <Grid item xs={6}>
              <MiniMetric
                label="매수"
                value={entryRates.buyRateLabel}
                tone={entryRates.buyRate !== null && entryRates.buyRate >= 50 ? 'positive' : 'neutral'}
              />
            </Grid>
            <Grid item xs={6}>
              <MiniMetric
                label="매도"
                value={entryRates.sellRateLabel}
                tone={entryRates.sellRate !== null && entryRates.sellRate >= 50 ? 'negative' : 'neutral'}
              />
            </Grid>
          </Grid>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: -0.5 }}>
            {entryRates.windowLabel}
            {entryRates.coveredSymbolCount > 0 ? ` · ${entryRates.coveredSymbolCount}개 심볼 평균` : ''}
          </Typography>

          <Divider sx={{ borderColor: theme.palette.border.soft, my: 1.75 }} />

          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary">
              활성 포지션
            </Typography>
            <Stack spacing={1} sx={{ mt: 1, minHeight: 92 }}>
              {strategy.open_positions.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  현재 열린 포지션이 없습니다.
                </Typography>
              ) : (
                strategy.open_positions.map((position) => (
                  <Box
                    key={`${strategy.strategy_id}-${position.symbol}`}
                    sx={{
                      borderRadius: '12px',
                      border: `1px solid ${theme.palette.border.soft}`,
                      backgroundColor: alpha(theme.palette.common.white, 0.008),
                      p: 1.25,
                    }}
                  >
                    <Stack direction="row" justifyContent="space-between" spacing={1}>
                      <Typography variant="body2" fontWeight={600}>
                        {position.symbol}
                      </Typography>
                      <Typography
                        variant="body2"
                        color={position.unrealized_pnl_pct >= 0 ? 'status.success' : 'status.danger'}
                        sx={{ fontVariantNumeric: 'tabular-nums' }}
                      >
                        {formatSignedPercent(position.unrealized_pnl_pct)}
                      </Typography>
                    </Stack>
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.4, display: 'block' }}>
                      {position.side} · {formatQuantity(position.quantity)}
                      {position.avg_entry_price ? ` @ ${formatKRW(position.avg_entry_price)}` : ''}
                    </Typography>
                  </Box>
                ))
              )}
            </Stack>
          </Box>

          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
            마지막 신호 {strategy.last_signal_at ? formatRelativeTime(strategy.last_signal_at) : '없음'}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}

function MarketDetailsSection({
  rows,
}: {
  rows: {
    symbol: string
    turnover_24h_krw: number | null
    surge_score: number | null
    selected: boolean
    active_compare_session_count: number
    has_open_position: boolean
    has_recent_signal: boolean
    risk_blocked: boolean
  }[]
}) {
  const theme = useTheme()

  if (rows.length === 0) {
    return <LabEmptyState message="마켓 상세 정보가 아직 없습니다." />
  }

  return (
    <Stack spacing={1.25}>
      {rows.slice(0, 12).map((row) => (
        <Accordion
          key={row.symbol}
          disableGutters
          sx={{
            borderRadius: '16px !important',
            border: `1px solid ${theme.palette.border.soft}`,
            backgroundColor: alpha(theme.palette.common.white, 0.008),
            '&:before': {
              display: 'none',
            },
            overflow: 'hidden',
          }}
        >
          <AccordionSummary expandIcon={<ChevronDown size={16} color={theme.palette.text.secondary} />}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ width: '100%', pr: 1 }}>
              <Box>
                <Typography variant="body1" fontWeight={600}>
                  {row.symbol}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  거래대금 {row.turnover_24h_krw === null ? '-' : formatCompactKRW(row.turnover_24h_krw)}
                </Typography>
              </Box>
              <Stack direction="row" spacing={0.75} sx={{ flexWrap: 'wrap', gap: 0.75 }}>
                {row.selected ? <Chip label="선택" size="small" sx={pillNeutralSx(theme)} /> : null}
                {row.has_open_position ? <Chip label="포지션" size="small" sx={pillSx(theme.palette.status.success)} /> : null}
                {row.has_recent_signal ? <Chip label="최근 신호" size="small" sx={pillSx(theme.palette.info.main)} /> : null}
                {row.risk_blocked ? <Chip label="리스크" size="small" sx={pillSx(theme.palette.status.warning)} /> : null}
              </Stack>
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <MiniMetric label="활성 비교 세션" value={String(row.active_compare_session_count)} tone="neutral" />
              </Grid>
              <Grid item xs={12} md={4}>
                <MiniMetric
                  label="Surge Score"
                  value={row.surge_score === null ? '-' : row.surge_score.toFixed(2)}
                  tone="neutral"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <MiniMetric
                  label="리스크 상태"
                  value={row.risk_blocked ? translateSeverity('WARNING') : '정상'}
                  tone={row.risk_blocked ? 'negative' : 'positive'}
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      ))}
    </Stack>
  )
}

function MiniMetric({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: 'positive' | 'negative' | 'neutral'
}) {
  const theme = useTheme()
  const color =
    tone === 'positive'
      ? theme.palette.status.success
      : tone === 'negative'
        ? theme.palette.status.danger
        : theme.palette.text.primary

  return (
    <Box
      sx={{
        height: '100%',
        borderRadius: '12px',
        border: `1px solid ${theme.palette.border.soft}`,
        backgroundColor: alpha(theme.palette.common.white, 0.008),
        p: 1.4,
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="body1"
        sx={{
          mt: 0.6,
          color,
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        {value}
      </Typography>
    </Box>
  )
}

function pillSx(color: string) {
  return {
    borderRadius: 999,
    color,
    backgroundColor: alpha(color, 0.08),
    border: `1px solid ${alpha(color, 0.14)}`,
    '& .MuiChip-icon': {
      color,
    },
  }
}

function pillNeutralSx(theme: Theme) {
  return {
    borderRadius: 999,
    color: theme.palette.text.secondary,
    backgroundColor: alpha(theme.palette.common.white, 0.02),
    border: `1px solid ${theme.palette.border.soft}`,
  }
}

function monitoringStateLabel(state: string) {
  switch (state) {
    case 'running':
      return '모니터링 중'
    case 'degraded':
      return '데이터 지연'
    default:
      return '대기'
  }
}

function monitoringStateChipSx(theme: Theme, state: string) {
  switch (state) {
    case 'running':
      return pillSx(theme.palette.status.success)
    case 'degraded':
      return pillSx(theme.palette.status.warning)
    default:
      return pillNeutralSx(theme)
  }
}

function aggregateEntryRates(symbols: string[], pricesBySymbol: Record<string, LiveSymbolPrice>) {
  const tracked = symbols
    .map((symbol) => pricesBySymbol[symbol])
    .filter((item): item is LiveSymbolPrice => item !== undefined)

  const buyValues = tracked
    .map((item) => item.buy_entry_rate_pct)
    .filter((value): value is number => value !== null)
  const sellValues = tracked
    .map((item) => item.sell_entry_rate_pct)
    .filter((value): value is number => value !== null)
  const windows = tracked
    .map((item) => item.entry_rate_window_sec)
    .filter((value): value is number => value !== null)

  const buyRate = buyValues.length ? buyValues.reduce((sum, value) => sum + value, 0) / buyValues.length : null
  const sellRate = sellValues.length ? sellValues.reduce((sum, value) => sum + value, 0) / sellValues.length : null
  const windowSec = windows.length ? windows[0] : null

  return {
    buyRate,
    sellRate,
    buyRateLabel: buyRate === null ? '-' : `${buyRate.toFixed(1)}%`,
    sellRateLabel: sellRate === null ? '-' : `${sellRate.toFixed(1)}%`,
    windowLabel:
      windowSec === null
        ? '진입률 데이터 대기 중'
        : windowSec % 60 === 0
          ? `최근 ${windowSec / 60}분 체결 기준`
          : `최근 ${windowSec}초 체결 기준`,
    coveredSymbolCount: tracked.length,
  }
}

function toneColor(theme: Theme, tone: string) {
  switch (tone) {
    case 'success':
      return theme.palette.status.success
    case 'danger':
      return theme.palette.status.danger
    case 'warning':
      return theme.palette.status.warning
    case 'info':
      return theme.palette.status.info
    default:
      return theme.palette.primary.main
  }
}

function formatCompactKRW(value: number) {
  const absolute = Math.abs(value)
  if (absolute >= 100_000_000) {
    return `${value < 0 ? '-' : ''}${(absolute / 100_000_000).toFixed(1)}억`
  }
  if (absolute >= 10_000) {
    return `${value < 0 ? '-' : ''}${(absolute / 10_000).toFixed(1)}만`
  }
  return formatKRW(value)
}

function formatSignedKRW(value: number) {
  return `${value > 0 ? '+' : ''}${formatKRW(value)}`
}

function formatSignedPercent(value: number) {
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

function formatQuantity(value: number) {
  return value.toLocaleString('ko-KR', {
    maximumFractionDigits: 4,
  })
}
