import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Checkbox,
  FormControlLabel,
  FormGroup,
  Skeleton,
  Chip,
} from '@mui/material'
import { AlertCircle } from 'lucide-react'

import { useSessions } from '@/features/sessions/api'
import { useUiStore } from '@/stores/ui-store'
import type { SessionStatus } from '@/entities/session/types'

function getStatusColor(status: SessionStatus) {
  switch (status) {
    case 'RUNNING':
      return 'status.success'
    case 'FAILED':
      return 'status.danger'
    case 'STOPPING':
      return 'status.warning'
    case 'PENDING':
      return 'status.info'
    default:
      return 'text.secondary'
  }
}

export default function ComparePage() {
  const { data: sessions, isLoading } = useSessions()
  const { selectedCompareSessionIds, setCompareSessionIds } = useUiStore()

  const handleToggleSession = (id: string) => {
    if (selectedCompareSessionIds.includes(id)) {
      setCompareSessionIds(selectedCompareSessionIds.filter(sId => sId !== id))
    } else {
      if (selectedCompareSessionIds.length < 4) {
        setCompareSessionIds([...selectedCompareSessionIds, id])
      }
    }
  }

  const selectedSessions = sessions?.filter(s => selectedCompareSessionIds.includes(s.id)) || []

  return (
    <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 600 }}>
        Compare Sessions
      </Typography>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Select Sessions to Compare (Max 4)</Typography>
          {isLoading ? (
            <Skeleton variant="rectangular" height={100} />
          ) : (
            <FormGroup row sx={{ gap: 2 }}>
              {sessions?.map(session => (
                <FormControlLabel
                  key={session.id}
                  control={
                    <Checkbox
                      checked={selectedCompareSessionIds.includes(session.id)}
                      onChange={() => handleToggleSession(session.id)}
                      disabled={!selectedCompareSessionIds.includes(session.id) && selectedCompareSessionIds.length >= 4}
                    />
                  }
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography sx={{ fontVariantNumeric: 'tabular-nums' }}>
                        {session.id.substring(0, 8)}
                      </Typography>
                      <Chip label={session.mode} size="small" variant="outlined" />
                      <Chip
                        label={session.status}
                        size="small"
                        sx={{
                          bgcolor: getStatusColor(session.status),
                          color: 'background.paper',
                          fontWeight: 600,
                          fontSize: '0.7rem',
                        }}
                      />
                    </Box>
                  }
                />
              ))}
              {(!sessions || sessions.length === 0) && (
                <Typography color="text.secondary">No sessions available.</Typography>
              )}
            </FormGroup>
          )}
        </CardContent>
      </Card>

      {selectedSessions.length < 2 ? (
        <Card>
          <CardContent sx={{ py: 8, textAlign: 'center' }}>
            <AlertCircle size={48} style={{ margin: '0 auto', opacity: 0.5, marginBottom: 16 }} />
            <Typography variant="h6" color="text.secondary">
              Select 2 or more sessions above to compare performance.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: 'text.tertiary', fontWeight: 600 }}>Metric</TableCell>
                {selectedSessions.map(session => (
                  <TableCell key={session.id} align="right" sx={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
                    {session.id.substring(0, 8)}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Total Return %</TableCell>
                {selectedSessions.map(session => {
                  const val = session.performance?.realized_pnl_pct ?? 0
                  return (
                    <TableCell
                      key={session.id}
                      align="right"
                      sx={{
                        fontVariantNumeric: 'tabular-nums',
                        color: val >= 0 ? 'status.success' : 'status.danger'
                      }}
                    >
                      {val > 0 ? '+' : ''}{val.toFixed(2)}%
                    </TableCell>
                  )
                })}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Max Drawdown %</TableCell>
                {selectedSessions.map(session => {
                  const val = session.performance?.max_drawdown_pct ?? 0
                  return (
                    <TableCell
                      key={session.id}
                      align="right"
                      sx={{
                        fontVariantNumeric: 'tabular-nums',
                        color: 'status.danger'
                      }}
                    >
                      {val.toFixed(2)}%
                    </TableCell>
                  )
                })}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Win Rate %</TableCell>
                {selectedSessions.map(session => {
                  const val = session.performance?.win_rate_pct ?? 0
                  return (
                    <TableCell key={session.id} align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                      {val.toFixed(2)}%
                    </TableCell>
                  )
                })}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Trade Count</TableCell>
                {selectedSessions.map(session => {
                  const val = session.performance?.trade_count ?? 0
                  return (
                    <TableCell key={session.id} align="right" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                      {val}
                    </TableCell>
                  )
                })}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Realized PnL Today</TableCell>
                {selectedSessions.map(session => {
                  const val = session.performance?.realized_pnl ?? 0
                  return (
                    <TableCell
                      key={session.id}
                      align="right"
                      sx={{
                        fontVariantNumeric: 'tabular-nums',
                        color: val >= 0 ? 'status.success' : 'status.danger'
                      }}
                    >
                      {val > 0 ? '+' : ''}{val.toFixed(2)}
                    </TableCell>
                  )
                })}
              </TableRow>
              <TableRow hover>
                <TableCell sx={{ color: 'text.secondary' }}>Unrealized PnL Now</TableCell>
                {selectedSessions.map(session => {
                  const val = session.performance?.unrealized_pnl ?? 0
                  return (
                    <TableCell
                      key={session.id}
                      align="right"
                      sx={{
                        fontVariantNumeric: 'tabular-nums',
                        color: val >= 0 ? 'status.success' : 'status.danger'
                      }}
                    >
                      {val > 0 ? '+' : ''}{val.toFixed(2)}
                    </TableCell>
                  )
                })}
              </TableRow>
            </TableBody>
          </Table>
        </Card>
      )}
    </Box>
  )
}
