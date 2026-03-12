import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Skeleton,
  Stack,
  IconButton,
  Collapse,
  Divider
} from '@mui/material'
import type { ChipProps } from '@mui/material'
import { Edit2, Play, ChevronDown, ChevronUp, ArrowLeft } from 'lucide-react'
import { useStrategy, useStrategyVersions } from '@/features/strategies/api'
import { useSessions } from '@/features/sessions/api'
import { useBacktests } from '@/features/backtests/api'
import { formatDistanceToNow, format } from 'date-fns'

export default function StrategyDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: strategy, isLoading: isLoadingStrategy } = useStrategy(id!)
  const { data: versions, isLoading: isLoadingVersions } = useStrategyVersions(id!)
  const { data: sessions } = useSessions()
  const { data: backtests } = useBacktests()

  const [jsonExpanded, setJsonExpanded] = useState(false)

  if (isLoadingStrategy || isLoadingVersions) {
    return (
      <Box>
        <Skeleton variant="rectangular" height={80} sx={{ mb: 3, borderRadius: 2 }} />
        <Skeleton variant="rectangular" height={200} sx={{ mb: 3, borderRadius: 2 }} />
        <Skeleton variant="rectangular" height={300} sx={{ borderRadius: 2 }} />
      </Box>
    )
  }

  if (!strategy) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h5" color="text.secondary" mb={2}>Strategy not found</Typography>
        <Button variant="contained" onClick={() => navigate('/strategies')}>Back to Strategies</Button>
      </Box>
    )
  }

  const latestVersion = versions?.[0]
  const strategyVersionIds = new Set((versions ?? []).map((version) => version.id))
  const relatedSessions = (sessions ?? []).filter((session) => strategyVersionIds.has(session.strategy_version_id) && session.status === 'RUNNING')
  const relatedBacktests = (backtests ?? []).filter((run) => strategyVersionIds.has(run.strategy_version_id))

  const getTypeColor = (type: string): ChipProps['color'] => {
    switch (type) {
      case 'dsl': return 'info'
      case 'plugin': return 'warning'
      case 'hybrid': return 'success'
      default: return 'default'
    }
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3, gap: 2 }}>
        <IconButton onClick={() => navigate('/strategies')} sx={{ color: 'text.secondary' }}>
          <ArrowLeft size={20} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Stack direction="row" alignItems="center" spacing={2}>
            <Typography variant="h4">{strategy.name}</Typography>
            <Chip 
              label={strategy.strategy_type.toUpperCase()} 
              size="small" 
              color={getTypeColor(strategy.strategy_type)}
            />
            <Box 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                color: strategy.is_active ? 'status.success' : 'text.disabled',
                typography: 'caption',
                fontWeight: 600
              }}
            >
              <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'currentColor' }} />
              {strategy.is_active ? 'ACTIVE' : 'INACTIVE'}
            </Box>
          </Stack>
          <Typography variant="body2" color="text.tertiary" sx={{ mt: 0.5 }}>
            {strategy.strategy_key}
          </Typography>
        </Box>
        <Button 
          variant="outlined" 
          startIcon={<Edit2 size={16} />}
          onClick={() => navigate(`/strategies/${strategy.id}/edit`)}
        >
          Edit
        </Button>
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<Play size={16} />}
          onClick={() => navigate('/backtests')}
        >
          Run Backtest
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {/* Latest Version Summary */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>Latest Version Summary</Typography>
              {latestVersion ? (
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">Version</Typography>
                    <Typography variant="body1">v{latestVersion.version_no}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">Schema</Typography>
                    <Typography variant="body1">{latestVersion.schema_version}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">Config Hash</Typography>
                    <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                      {latestVersion.config_hash.substring(0, 8)}...
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">Validated</Typography>
                    <Typography variant="body1">{latestVersion.is_validated ? 'Yes' : 'No'}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">Created</Typography>
                    <Typography variant="body1">
                      {formatDistanceToNow(new Date(latestVersion.created_at), { addSuffix: true })}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="caption" color="text.tertiary">Labels</Typography>
                    <Stack direction="row" spacing={1} mt={0.5}>
                      {latestVersion.labels.length > 0 ? (
                        latestVersion.labels.map(label => (
                          <Chip key={label} label={label} size="small" variant="outlined" />
                        ))
                      ) : (
                        <Typography variant="body2" color="text.disabled">None</Typography>
                      )}
                    </Stack>
                  </Grid>
                  {latestVersion.notes && (
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.tertiary">Notes</Typography>
                      <Typography variant="body2" sx={{ mt: 0.5, p: 1.5, bgcolor: 'bg.surface2', borderRadius: 1 }}>
                        {latestVersion.notes}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              ) : (
                <Typography color="text.secondary">No versions found.</Typography>
              )}
            </CardContent>
          </Card>

          {/* JSON Preview */}
          {latestVersion && (
            <Card sx={{ mb: 3 }}>
              <Box 
                sx={{ 
                  p: 2, 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' }
                }}
                onClick={() => setJsonExpanded(!jsonExpanded)}
              >
                <Typography variant="h6">Configuration JSON</Typography>
                <IconButton size="small">
                  {jsonExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                </IconButton>
              </Box>
              <Collapse in={jsonExpanded}>
                <Divider />
                <Box sx={{ p: 2, bgcolor: 'bg.surface2', overflowX: 'auto' }}>
                  <pre style={{ margin: 0, color: 'var(--mui-palette-text-secondary)', fontSize: 13, fontFamily: 'monospace' }}>
                    {JSON.stringify(latestVersion.config_json, null, 2)}
                  </pre>
                </Box>
              </Collapse>
            </Card>
          )}

          {/* Version History */}
          <Card>
            <CardContent sx={{ pb: 0 }}>
              <Typography variant="h6" mb={2}>Version History</Typography>
            </CardContent>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
                    <TableCell>Version</TableCell>
                    <TableCell>Labels</TableCell>
                    <TableCell>Notes</TableCell>
                    <TableCell>Created</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {versions?.map((v) => (
                    <TableRow key={v.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight={v.version_no === strategy.latest_version_no ? 600 : 400}>
                          v{v.version_no}
                          {v.version_no === strategy.latest_version_no && (
                            <Chip label="LATEST" size="small" color="primary" sx={{ ml: 1, height: 16, fontSize: 9 }} />
                          )}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5}>
                          {v.labels.slice(0, 2).map(l => (
                            <Chip key={l} label={l} size="small" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
                          ))}
                          {v.labels.length > 2 && (
                            <Chip label={`+${v.labels.length - 2}`} size="small" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 200 }}>
                          {v.notes || '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {format(new Date(v.created_at), 'MMM d, yyyy HH:mm')}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!versions?.length && (
                    <TableRow>
                      <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                        <Typography color="text.secondary">No version history</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          {/* Performance Card */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>Performance</Typography>
              {strategy.last_7d_return_pct !== null ? (
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.tertiary">7d Return</Typography>
                    <Typography 
                      variant="h5" 
                      sx={{ 
                        color: strategy.last_7d_return_pct >= 0 ? 'status.success' : 'status.danger',
                        fontVariantNumeric: 'tabular-nums'
                      }}
                    >
                      {strategy.last_7d_return_pct > 0 ? '+' : ''}{strategy.last_7d_return_pct.toFixed(2)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.tertiary">Win Rate</Typography>
                    <Typography variant="h5" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                      {strategy.last_7d_win_rate !== null ? `${(strategy.last_7d_win_rate * 100).toFixed(1)}%` : '-'}
                    </Typography>
                  </Grid>
                </Grid>
              ) : (
                <Typography color="text.secondary" variant="body2">No performance data available.</Typography>
              )}
            </CardContent>
          </Card>

          {/* Related Backtests */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>Recent Backtests</Typography>
              {relatedBacktests.length === 0 ? (
                <Typography color="text.secondary" variant="body2">No backtests for this strategy.</Typography>
              ) : (
                <Stack spacing={1.5}>
                  {relatedBacktests.slice(0, 4).map((run) => (
                    <Box key={run.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'bg.surface2' }}>
                      <Typography variant="body2" fontWeight={600}>{run.id.substring(0, 8)}</Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {run.status} · {run.metrics?.trade_count ?? 0} trades
                      </Typography>
                      <Typography variant="caption" sx={{ color: (run.metrics?.total_return_pct ?? 0) >= 0 ? 'status.success' : 'status.danger' }}>
                        {(run.metrics?.total_return_pct ?? 0).toFixed(2)}% return
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>

          {/* Related Sessions */}
          <Card>
            <CardContent>
              <Typography variant="h6" mb={2}>Active Sessions</Typography>
              {relatedSessions.length === 0 ? (
                <Typography color="text.secondary" variant="body2">No sessions for this strategy.</Typography>
              ) : (
                <Stack spacing={1.5}>
                  {relatedSessions.slice(0, 4).map((session) => (
                    <Box key={session.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'bg.surface2' }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" fontWeight={600}>{session.id.substring(0, 8)}</Typography>
                        <Chip label={session.mode} size="small" variant="outlined" />
                      </Stack>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {session.status} · {(session.symbol_scope.active_symbols ?? []).length} active symbols
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
