import { useState } from 'react'
import {
  Box,
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
import { translateBacktestStatus } from '@/shared/lib/i18n'
import { LabEmptyState } from '@/shared/ui/LabEmptyState'
import { LabPageHeader } from '@/shared/ui/LabPageHeader'
import { LabSurfaceCard } from '@/shared/ui/LabSurfaceCard'

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
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <LabPageHeader
        eyebrow="COMPARISON BOARD"
        title="백테스트 비교"
        description="선택한 백테스트 실행을 같은 지표 축에서 비교해 개선 방향을 빠르게 읽습니다."
      />

      <LabSurfaceCard variant="low" headerDivider={false}>
          <Typography variant="h6" gutterBottom>비교할 백테스트 실행 선택 (최대 4개)</Typography>
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
                  label={`${run.id.substring(0, 8)} · ${run.strategy_version_id.substring(0, 8)} · ${translateBacktestStatus(run.status)}`}
                />
              ))}
              {(!backtests || backtests.length === 0) ? (
                <Typography color="text.secondary">사용 가능한 백테스트 실행이 없습니다.</Typography>
              ) : null}
            </FormGroup>
          )}
      </LabSurfaceCard>

      {selectedRuns.length < 2 ? (
        <LabSurfaceCard variant="container" headerDivider={false}>
          <Box sx={{ py: 4 }}>
            <AlertCircle size={40} style={{ margin: '0 auto 16px', opacity: 0.42 }} />
            <LabEmptyState message="위에서 백테스트 실행 2개 이상을 선택하면 성과를 비교할 수 있습니다." minHeight={180} />
          </Box>
        </LabSurfaceCard>
      ) : (
        <LabSurfaceCard variant="container" headerDivider={false}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: 'text.tertiary', fontWeight: 600 }}>지표</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                    {run.id.substring(0, 8)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>총 수익률 %</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right" sx={{ color: (run.metrics?.total_return_pct ?? 0) >= 0 ? 'status.success' : 'status.danger' }}>
                    {(run.metrics?.total_return_pct ?? 0).toFixed(2)}%
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>최대 낙폭 %</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right" sx={{ color: 'status.danger' }}>
                    {(run.metrics?.max_drawdown_pct ?? 0).toFixed(2)}%
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>승률 %</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right">
                    {(run.metrics?.win_rate_pct ?? 0).toFixed(2)}%
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>손익비</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right">
                    {(run.metrics?.profit_factor ?? 0).toFixed(2)}
                  </TableCell>
                ))}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>거래 수</TableCell>
                {selectedRuns.map((run) => (
                  <TableCell key={run.id} align="right">
                    {run.metrics?.trade_count ?? 0}
                  </TableCell>
                ))}
              </TableRow>
            </TableBody>
          </Table>
        </LabSurfaceCard>
      )}
    </Box>
  )
}
