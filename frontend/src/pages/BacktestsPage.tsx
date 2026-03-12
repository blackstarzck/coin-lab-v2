import { useState } from 'react'
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
import { format, formatDistanceToNow } from 'date-fns'

import {
  useBacktests,
  useBacktest,
  useRunBacktest,
  useBacktestTrades,
  useBacktestEquityCurve,
} from '@/features/backtests/api'
import { useStrategies } from '@/features/strategies/api'
import { LineChart } from '@/shared/charts/LineChart'
import type { BacktestRunStatus } from '@/entities/backtest/types'

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

export default function BacktestsPage() {
  const [tab, setTab] = useState(0)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTab(newValue)
  }

  const handleSelectRun = (id: string) => {
    setSelectedRunId(id)
    setTab(2) // Switch to Results tab
  }

  return (
    <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Backtests
        </Typography>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'border.default' }}>
        <Tabs value={tab} onChange={handleTabChange}>
          <Tab icon={<Play size={18} />} iconPosition="start" label="Run New" />
          <Tab icon={<History size={18} />} iconPosition="start" label="History" />
          <Tab icon={<BarChart2 size={18} />} iconPosition="start" label="Results" disabled={!selectedRunId && tab !== 2} />
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
  const [symbols, setSymbols] = useState('BTCUSDT,ETHUSDT')
  const [timeframes, setTimeframes] = useState('1h,4h')
  const [dateFrom, setDateFrom] = useState('2023-01-01')
  const [dateTo, setDateTo] = useState('2023-12-31')
  const [initialCapital, setInitialCapital] = useState('10000')

  const handleRun = async () => {
    if (!strategyId) return

    const strategy = strategies?.find(s => s.id === strategyId)
    if (!strategy || !strategy.latest_version_id) return

    try {
      const result = await runBacktest.mutateAsync({
        strategy_version_id: strategy.latest_version_id,
        symbols: symbols.split(',').map(s => s.trim()),
        timeframes: timeframes.split(',').map(s => s.trim()),
        date_from: new Date(dateFrom).toISOString(),
        date_to: new Date(dateTo).toISOString(),
        initial_capital: Number(initialCapital),
      })
      if (result && result.id) {
        onRunCreated(result.id)
      }
    } catch (error) {
      console.error('Failed to run backtest', error)
    }
  }

  return (
    <Card>
      <CardContent sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <Typography variant="h6">Configure Backtest</Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <FormControl fullWidth>
              <InputLabel>Strategy</InputLabel>
              <Select
                value={strategyId}
                label="Strategy"
                onChange={(e) => setStrategyId(e.target.value)}
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
              label="Initial Capital"
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              inputProps={{ style: { fontVariantNumeric: 'tabular-nums' } }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Symbols (comma separated)"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Timeframes (comma separated)"
              value={timeframes}
              onChange={(e) => setTimeframes(e.target.value)}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Date From"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Date To"
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
            {runBacktest.isPending ? 'Starting...' : 'Run Backtest'}
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
            No backtests yet. Run your first backtest to see results.
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
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Status</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Strategy Version</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Symbols</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Date Range</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">Return</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">MDD</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">Win Rate</TableCell>
            <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">Created</TableCell>
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
                  label={run.status}
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
                {format(new Date(run.date_from), 'MMM d, yy')} - {format(new Date(run.date_to), 'MMM d, yy')}
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
                {formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}
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
            Select a backtest from History to view details
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
                Total Return
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
                Max Drawdown
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
                Win Rate
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
                Profit Factor
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
                Trade Count
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
                Avg Hold (min)
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
                Sharpe Ratio
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
          <Typography variant="h6" gutterBottom>Equity Curve</Typography>
          <Box sx={{ height: 400 }}>
            {chartData.length > 0 ? (
              <LineChart data={chartData} height={400} />
            ) : (
              <Box sx={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Typography color="text.secondary">No equity curve data available</Typography>
              </Box>
            )}
          </Box>
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ pb: 0 }}>
          <Typography variant="h6" gutterBottom>Trades ({run.metrics?.trade_count || 0})</Typography>
        </CardContent>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Symbol</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Entry Time</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Exit Time</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">Entry Price</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">Exit Price</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">Qty</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">PnL</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }} align="right">PnL %</TableCell>
              <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Reason</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {trades?.map((trade) => (
              <TableRow key={trade.id} hover>
                <TableCell>{trade.symbol}</TableCell>
                <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {format(new Date(trade.entry_time), 'MM/dd HH:mm')}
                </TableCell>
                <TableCell sx={{ fontVariantNumeric: 'tabular-nums' }}>
                  {format(new Date(trade.exit_time), 'MM/dd HH:mm')}
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
                  <Chip label={trade.exit_reason} size="small" variant="outlined" />
                </TableCell>
              </TableRow>
            ))}
            {(!trades || trades.length === 0) && (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                  No trades executed in this backtest
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Card>
    </Box>
  )
}
