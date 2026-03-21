import { useMemo, useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tabs,
  Tab,
  TextField,
  Select,
  MenuItem,
  Button,
  Chip,
  InputLabel,
  FormControl,
  Skeleton,
} from '@mui/material'
import { Play, History, BarChart2, AlertCircle } from 'lucide-react'

import {
  useBacktests,
  useBacktest,
  useRunBacktest,
  useBacktestTrades,
  useBacktestEquityCurve,
} from '@/features/backtests/api'
import { useStrategies, useStrategyVersions } from '@/features/strategies/api'
import { LineChart } from '@/shared/charts/LineChart'
import type { BacktestRunStatus } from '@/entities/backtest/types'
import { getStrategyStaticSymbols } from '@/entities/strategy/config'
import {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  translateBacktestStatus,
  translateExitReason,
} from '@/shared/lib/i18n'
import { LabPageHeader } from '@/shared/ui/LabPageHeader'

function getStatusColor(status: BacktestRunStatus) {
  switch (status) {
    case 'COMPLETED':
      return 'status.success'
    case 'FAILED':
      return 'status.danger'
    case 'RUNNING':
      return 'status.warning'
    case 'QUEUED':
      return 'status.info'
    default:
      return 'text.secondary'
  }
}

const DEFAULT_SYMBOLS_INPUT = 'KRW-BTC, KRW-ETH'

export default function BacktestsPage() {
  const [tab, setTab] = useState(0)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTab(newValue)
  }

  const handleSelectRun = (id: string) => {
    setSelectedRunId(id)
      setTab(2)
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <LabPageHeader
        eyebrow="BACKTEST LAB"
        title="백테스트"
        description="전략 실행 규칙을 재현하고 기간별 성과를 검증하는 실험실입니다."
      />

      <Box sx={{ borderBottom: 1, borderColor: 'border.default' }}>
        <Tabs value={tab} onChange={handleTabChange}>
          <Tab icon={<Play size={18} />} iconPosition="start" label="새 실행" />
          <Tab icon={<History size={18} />} iconPosition="start" label="이력" />
          <Tab icon={<BarChart2 size={18} />} iconPosition="start" label="결과" disabled={!selectedRunId && tab !== 2} />
        </Tabs>
      </Box>

      {tab === 0 && <RunNewTab onRunCreated={handleSelectRun} />}
      {tab === 1 && <HistoryTab onSelectRun={handleSelectRun} />}
      {tab === 2 && <ResultsTab runId={selectedRunId} />}
    </Box>
  )
}

function RunNewTab({ onRunCreated }: { onRunCreated: (id: string) => void }) {
  const { data: strategies, isLoading: isLoadingStrategies } = useStrategies()
  const runBacktest = useRunBacktest()

  const [strategyId, setStrategyId] = useState('')
  const [symbolsOverride, setSymbolsOverride] = useState<string | null>(null)
  const [timeframes, setTimeframes] = useState('1h,4h')
  const [dateFrom, setDateFrom] = useState('2023-01-01')
  const [dateTo, setDateTo] = useState('2023-12-31')
  const [initialCapital, setInitialCapital] = useState('10000')
  const { data: strategyVersions } = useStrategyVersions(strategyId)

  const derivedSymbols = useMemo(() => {
    if (!strategyId) {
      return DEFAULT_SYMBOLS_INPUT
    }

    const defaultSymbols = getStrategyStaticSymbols((strategyVersions?.[0]?.config_json ?? {}) as Record<string, unknown>)
    return defaultSymbols.length > 0 ? defaultSymbols.join(', ') : DEFAULT_SYMBOLS_INPUT
  }, [strategyId, strategyVersions])
  const symbols = symbolsOverride ?? derivedSymbols

  const handleRun = async () => {
    if (!strategyId) return

    const strategy = strategies?.find(s => s.id === strategyId)
    if (!strategy || !strategy.latest_version_id) return

    try {
      const result = await runBacktest.mutateAsync({
        strategy_version_id: strategy.latest_version_id,
        symbols: symbols.split(',').map(s => s.trim()).filter(Boolean),
        timeframes: timeframes.split(',').map(s => s.trim()),
        date_from: new Date(dateFrom).toISOString(),
        date_to: new Date(dateTo).toISOString(),
        initial_capital: Number(initialCapital),
      })
      if (result && result.id) {
        onRunCreated(result.id)
      }
    } catch (error) {
      console.error('백테스트 실행에 실패했습니다', error)
    }
  }

  return (
    <Card>
      <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Typography variant="h6">백테스트 설정</Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>전략</InputLabel>
              <Select
                value={strategyId}
                label="전략"
                onChange={(e) => {
                  setStrategyId(e.target.value)
                  setSymbolsOverride(null)
                }}
                disabled={isLoadingStrategies}
              >
                {strategies?.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name} {s.latest_version_no ? `(v${s.latest_version_no})` : ''}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="초기 자본"
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              inputProps={{ style: { fontVariantNumeric: 'tabular-nums' } }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="심볼 (쉼표로 구분)"
              value={symbols}
              onChange={(e) => setSymbolsOverride(e.target.value)}
              helperText="정적 전략은 기본 코인 목록이 자동 입력됩니다. 비우면 전략 기본값을 사용합니다."
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="타임프레임 (쉼표로 구분)"
              value={timeframes}
              onChange={(e) => setTimeframes(e.target.value)}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="시작일"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="종료일"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>
        </Grid>

        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
          <Button
            variant="contained"
            color="primary"
            size="large"
            onClick={handleRun}
            disabled={!strategyId || runBacktest.isPending}
            startIcon={<Play size={18} />}
          >
            {runBacktest.isPending ? '시작 중...' : '백테스트 실행'}
          </Button>
        </Box>
      </CardContent>
    </Card>
  )
}

function HistoryTab({ onSelectRun }: { onSelectRun: (id: string) => void }) {
  const { data: backtests, isLoading } = useBacktests()

  if (isLoading) {
    return <Skeleton variant="rectangular" height={400} />
  }

  if (!backtests || backtests.length === 0) {
    return (
      <Card>
        <CardContent sx={{ py: 8, textAlign: 'center' }}>
          <AlertCircle size={48} style={{ margin: '0 auto', opacity: 0.5, marginBottom: 16 }} />
          <Typography variant="h6" color="text.secondary">
            아직 백테스트가 없습니다. 첫 백테스트를 실행해 결과를 확인하세요.
          </Typography>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>ID</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>상태</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>전략 버전</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>심볼</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>기간</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">수익률</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">MDD</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">승률</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">생성 시각</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {backtests.map((run) => (
            <TableRow
              key={run.id}
              hover
              onClick={() => onSelectRun(run.id)}
              sx={{ cursor: 'pointer' }}
            >
              <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.id.substring(0, 8)}
              </TableCell>
              <TableCell>
                <Chip
                  label={translateBacktestStatus(run.status)}
                  size="small"
                  sx={{
                    bgcolor: getStatusColor(run.status),
                    color: 'background.paper',
                    fontWeight: 600,
                    fontSize: '0.7rem',
                  }}
                />
              </TableCell>
              <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.strategy_version_id.substring(0, 8)}
              </TableCell>
              <TableCell>{run.symbols.join(', ')}</TableCell>
              <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {formatDate(run.date_from)} - {formatDate(run.date_to)}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', color: run.metrics?.total_return_pct >= 0 ? 'status.success' : 'status.danger' }}>
                {run.metrics?.total_return_pct != null ? `${run.metrics.total_return_pct.toFixed(2)}%` : '-'}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', color: 'status.danger' }}>
                {run.metrics?.max_drawdown_pct != null ? `${run.metrics.max_drawdown_pct.toFixed(2)}%` : '-'}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.metrics?.win_rate_pct != null ? `${run.metrics.win_rate_pct.toFixed(2)}%` : '-'}
              </TableCell>
              <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums', color: 'text.secondary' }}>
                {formatRelativeTime(run.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

function ResultsTab({ runId }: { runId: string | null }) {
  const { data: run, isLoading: isLoadingRun } = useBacktest(runId || '')
  const { data: trades, isLoading: isLoadingTrades } = useBacktestTrades(runId || '')
  const { data: equityCurve, isLoading: isLoadingEquity } = useBacktestEquityCurve(runId || '')

  if (!runId) {
    return (
      <Card>
        <CardContent sx={{ py: 8, textAlign: 'center' }}>
          <BarChart2 size={48} style={{ margin: '0 auto', opacity: 0.5, marginBottom: 16 }} />
          <Typography variant="h6" color="text.secondary">
            이력 탭에서 백테스트를 선택해 상세 결과를 확인하세요
          </Typography>
        </CardContent>
      </Card>
    )
  }

  if (isLoadingRun || isLoadingTrades || isLoadingEquity) {
    return <Skeleton variant="rectangular" height={600} />
  }

  if (!run) return null

  const chartData = equityCurve?.map(p => ({
    time: p.time,
    value: p.equity
  })) || []

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                총 수익률
              </Typography>
              <Typography
                variant="h4"
                sx={{
                  fontVariantNumeric: 'tabular-nums',
                  color: run.metrics?.total_return_pct >= 0 ? 'status.success' : 'status.danger'
                }}
              >
                {run.metrics?.total_return_pct != null ? `${run.metrics.total_return_pct.toFixed(2)}%` : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                최대 낙폭
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums', color: 'status.danger' }}>
                {run.metrics?.max_drawdown_pct != null ? `${run.metrics.max_drawdown_pct.toFixed(2)}%` : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                승률
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.metrics?.win_rate_pct != null ? `${run.metrics.win_rate_pct.toFixed(2)}%` : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                손익비
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.metrics?.profit_factor != null ? run.metrics.profit_factor.toFixed(2) : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                거래 수
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.metrics?.trade_count != null ? run.metrics.trade_count : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                평균 보유 시간(분)
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.metrics?.avg_hold_minutes != null ? run.metrics.avg_hold_minutes.toFixed(1) : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                샤프 지수
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {run.metrics?.sharpe_ratio != null ? run.metrics.sharpe_ratio.toFixed(2) : '-'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>자산 곡선</Typography>
          <Box sx={{ height: 400 }}>
            {chartData.length > 0 ? (
              <LineChart data={chartData} height={400} />
            ) : (
              <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography color="text.secondary">자산 곡선 데이터가 없습니다</Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ pb: 0 }}>
          <Typography variant="h6" gutterBottom>거래 ({run.metrics?.trade_count || 0})</Typography>
        </CardContent>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>심볼</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>진입 시각</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>청산 시각</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">진입가</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">청산가</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">수량</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">손익</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">손익률</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>사유</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {trades?.map((trade) => (
              <TableRow key={trade.id} hover>
                <TableCell>{trade.symbol}</TableCell>
                <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {formatDateTime(trade.entry_time)}
                </TableCell>
                <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {formatDateTime(trade.exit_time)}
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {trade.entry_price.toFixed(2)}
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {trade.exit_price.toFixed(2)}
                </TableCell>
                <TableCell align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {trade.qty.toFixed(4)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: 'tabular-nums',
                    color: trade.pnl >= 0 ? 'status.success' : 'status.danger'
                  }}
                >
                  {trade.pnl > 0 ? '+' : ''}{trade.pnl.toFixed(2)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: 'tabular-nums',
                    color: trade.pnl_pct >= 0 ? 'status.success' : 'status.danger'
                  }}
                >
                  {trade.pnl_pct > 0 ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
                </TableCell>
                <TableCell>
                  <Chip label={translateExitReason(trade.exit_reason)} size="small" variant="outlined" />
                </TableCell>
              </TableRow>
            ))}
            {(!trades || trades.length === 0) && (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  이 백테스트에서는 거래가 발생하지 않았습니다
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Box>
  )
}
