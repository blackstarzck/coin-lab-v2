import { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { AlertCircle } from 'lucide-react'

import { useBacktests } from '@/features/backtests/api'

export default function ComparePage() {
  const { data: backtests, isLoading } = useBacktests()
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([])

  const toggleRun = (id: string) => {
    if (selectedRunIds.includes(id)) {
      setSelectedRunIds(selectedRunIds.filter((runId) => runId !== id))
      return
    }
    if (selectedRunIds.length < 4) {
      setSelectedRunIds([...selectedRunIds, id])
    }
  }

  const selectedRuns = (backtests ?? []).filter((run) => selectedRunIds.includes(run.id))

  return (
    <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 600 }}>Compare Backtests</Typography>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Select Backtest Runs to Compare (Max 4)</Typography>
          {isLoading ? (
            <Skeleton variant="rectangular" height={100} />
          ) : (
            <FormGroup row sx={{ gap: 2 }}>
              {(backtests ?? []).map((run) => (
                <FormControlLabel
                  key={run.id}
                  control={(
                    <Checkbox
                      checked={selectedRunIds.includes(run.id)}
                      onChange={() => toggleRun(run.id)}
                      disabled={!selectedRunIds.includes(run.id) && selectedRunIds.length >= 4}
                    />
                  )}
                  label={`${run.id.substring(0, 8)} · ${run.strategy_version_id.substring(0, 8)} · ${run.status}`}
                />
              ))}
              {(!backtests || backtests.length === 0) ? (
                <Typography color="text.secondary">No backtest runs available.</Typography>
              ) : null}
            </FormGroup>
          )}
        </CardContent>
      </Card>

      {selectedRuns.length < 2 ? (
        <Card>
          <CardContent sx={{ py: 8, textAlign: 'center' }}>
            <AlertCircle size={48} style={{ margin: '0 auto', opacity: 0.5, marginBottom: 16 }} />
            <Typography variant="h6" color="text.secondary">
              Select 2 or more backtest runs above to compare performance.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: 'text.tertiary', fontWeight: 600 }}>Metric</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                    {run.id.substring(0, 8)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Total Return %</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right" sx={{ color: (run.metrics?.total_return_pct ?? 0) >= 0 ? 'status.success' : 'status.danger' }}>
                    {(run.metrics?.total_return_pct ?? 0).toFixed(2)}%
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Max Drawdown %</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right" sx={{ color: 'status.danger' }}>
                    {(run.metrics?.max_drawdown_pct ?? 0).toFixed(2)}%
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Win Rate %</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right">
                    {(run.metrics?.win_rate_pct ?? 0).toFixed(2)}%
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Profit Factor</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right">
                    {(run.metrics?.profit_factor ?? 0).toFixed(2)}
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Trade Count</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right">
                    {run.metrics?.trade_count ?? 0}
                  </TableCell>
                ))}
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      )}
    </Box>
  )
}
