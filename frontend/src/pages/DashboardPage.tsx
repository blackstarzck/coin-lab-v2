import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Skeleton,
  Stack,
  useTheme
} from '@mui/material'
import { Activity, AlertTriangle, CheckCircle2, Clock, PlayCircle, XCircle } from 'lucide-react'
import { useMonitoringSummary } from '@/features/monitoring/api'
import { formatDistanceToNow, format } from 'date-fns'

export default function DashboardPage() {
  const navigate = useNavigate()
  const theme = useTheme()
  const { data: summary, isLoading } = useMonitoringSummary()

  const totalRealizedPnl = useMemo(() => {
    if (!summary?.strategy_cards) return 0
    return summary.strategy_cards.reduce((sum, card) => sum + (card.last_7d_return_pct || 0), 0)
  }, [summary])

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL': return 'error'
      case 'HIGH': return 'error'
      case 'MEDIUM': return 'warning'
      case 'LOW': return 'info'
      default: return 'default'
    }
  }

  const getActionColor = (action: string) => {
    return action === 'ENTER' ? 'success' : 'error'
  }

  if (isLoading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ mb: 3 }}>Dashboard</Typography>
        <Grid container spacing={2} sx={{ mb: 4 }}>
          {Array.from(new Array(6)).map((_, i) => (
            <Grid item xs={6} sm={4} md={2} key={i}>
              <Skeleton variant="rounded" height={40} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {Array.from(new Array(4)).map((_, i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Skeleton variant="rounded" height={100} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rounded" height={400} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rounded" height={400} />
          </Grid>
        </Grid>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" sx={{ mb: 3 }}>Dashboard</Typography>
      
      {/* Status Bar Row */}
      <Stack direction="row" spacing={2} sx={{ mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Chip 
          icon={<PlayCircle size={16} />} 
          label={`${summary?.status_bar.running_session_count || 0} Running`} 
          color="success" 
          variant="outlined" 
        />
        <Chip 
          icon={<Activity size={16} />} 
          label={`${summary?.status_bar.paper_session_count || 0} Paper`} 
          color="info" 
          variant="outlined" 
        />
        <Chip 
          icon={<Activity size={16} />} 
          label={`${summary?.status_bar.live_session_count || 0} Live`} 
          color="error" 
          variant="outlined" 
        />
        <Chip 
          icon={<XCircle size={16} />} 
          label={`${summary?.status_bar.failed_session_count || 0} Failed`} 
          color="error" 
          variant="outlined" 
        />
        <Chip 
          icon={<AlertTriangle size={16} />} 
          label={`${summary?.status_bar.degraded_session_count || 0} Degraded`} 
          color="warning" 
          variant="outlined" 
        />
        <Chip 
          icon={<CheckCircle2 size={16} />} 
          label={`${summary?.status_bar.active_symbol_count || 0} Active Symbols`} 
          color="default" 
          variant="outlined" 
        />
      </Stack>

      {/* KPI Cards Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Running Sessions
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {summary?.status_bar.running_session_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Active Symbols
              </Typography>
              <Typography variant="h4" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                {summary?.status_bar.active_symbol_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Total 7d Return (Sum)
              </Typography>
              <Typography 
                variant="h4" 
                sx={{ 
                  color: totalRealizedPnl >= 0 ? 'status.success' : 'status.danger',
                  fontVariantNumeric: 'tabular-nums' 
                }}
              >
                {totalRealizedPnl > 0 ? '+' : ''}{totalRealizedPnl.toFixed(2)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom variant="body2">
                Risk Alerts
              </Typography>
              <Typography 
                variant="h4" 
                sx={{ 
                  color: (summary?.risk_overview.active_alert_count || 0) > 0 ? 'status.danger' : 'text.primary',
                  fontVariantNumeric: 'tabular-nums' 
                }}
              >
                {summary?.risk_overview.active_alert_count || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Strategy Summary Cards */}
      <Typography variant="h6" sx={{ mb: 2 }}>Active Strategies</Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {summary?.strategy_cards.length === 0 ? (
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ py: 4, textAlign: 'center' }}>
                <Typography color="text.secondary">No active strategies. Start a session to see data here.</Typography>
              </CardContent>
            </Card>
          </Grid>
        ) : (
          summary?.strategy_cards.map((strategy) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={strategy.strategy_id}>
              <Card 
                sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}
                onClick={() => navigate(`/strategies/${strategy.strategy_id}`)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Box>
                      <Typography variant="subtitle1" fontWeight={600} noWrap title={strategy.strategy_name}>
                        {strategy.strategy_name}
                      </Typography>
                      <Typography variant="caption" color="text.tertiary">
                        v{strategy.latest_version_no}
                      </Typography>
                    </Box>
                    <Box 
                      sx={{ 
                        width: 8, 
                        height: 8, 
                        borderRadius: '50%', 
                        bgcolor: strategy.is_active ? 'status.success' : 'text.disabled',
                        mt: 1
                      }} 
                    />
                  </Box>
                  
                  <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                    <Chip 
                      label={strategy.strategy_type.toUpperCase()} 
                      size="small" 
                      variant="outlined"
                      sx={{ fontSize: 10, height: 20 }}
                    />
                    <Chip 
                      icon={<PlayCircle size={12} />}
                      label={`${strategy.active_session_count} Sessions`} 
                      size="small" 
                      variant="outlined"
                      sx={{ fontSize: 10, height: 20 }}
                    />
                  </Stack>

                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary" display="block">
                        7d Return
                      </Typography>
                      <Typography 
                        variant="body1" 
                        fontWeight={600}
                        sx={{ 
                          color: strategy.last_7d_return_pct >= 0 ? 'status.success' : 'status.danger',
                          fontVariantNumeric: 'tabular-nums'
                        }}
                      >
                        {strategy.last_7d_return_pct > 0 ? '+' : ''}{strategy.last_7d_return_pct.toFixed(2)}%
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        Last Signal
                      </Typography>
                      <Typography variant="caption" color="text.primary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Clock size={12} />
                        {strategy.last_signal_at ? formatDistanceToNow(new Date(strategy.last_signal_at), { addSuffix: true }) : 'Never'}
                      </Typography>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))
        )}
      </Grid>

      {/* Bottom Panels */}
      <Grid container spacing={3}>
        {/* Risk Alerts Panel */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', minHeight: 400 }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">Risk Alerts</Typography>
                <Stack direction="row" spacing={1}>
                  {summary?.risk_overview.blocked_signal_count_1h ? (
                    <Chip label={`${summary.risk_overview.blocked_signal_count_1h} Blocked (1h)`} size="small" color="warning" />
                  ) : null}
                </Stack>
              </Box>
              
              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
                      <TableCell>Time</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Code</TableCell>
                      <TableCell>Message</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!summary?.risk_overview.items || summary.risk_overview.items.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} align="center" sx={{ py: 8 }}>
                          <Typography color="text.secondary">No active risk alerts</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      summary.risk_overview.items.map((alert, i) => (
                        <TableRow key={i} hover>
                          <TableCell sx={{ whiteSpace: 'nowrap' }}>
                            <Typography variant="caption" color="text.secondary">
                              {format(new Date(alert.created_at), 'HH:mm:ss')}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={alert.severity} 
                              size="small" 
                              sx={{ 
                                fontSize: 10, 
                                height: 20,
                                bgcolor: getSeverityColor(alert.severity) === 'default' ? 'action.disabledBackground' : `status.${getSeverityColor(alert.severity)}`,
                                color: getSeverityColor(alert.severity) === 'default' ? 'text.secondary' : 'white'
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" fontFamily="monospace">
                              {alert.code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" noWrap title={alert.message} sx={{ maxWidth: 200 }}>
                              {alert.message}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Signals Feed */}
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', minHeight: 400 }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="h6">Recent Signals</Typography>
              </Box>
              
              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
                      <TableCell>Time</TableCell>
                      <TableCell>Symbol</TableCell>
                      <TableCell>Action</TableCell>
                      <TableCell align="right">Price</TableCell>
                      <TableCell align="right">Confidence</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!summary?.recent_signals || summary.recent_signals.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                          <Typography color="text.secondary">No recent signals</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      summary.recent_signals.map((signal) => (
                        <TableRow 
                          key={signal.id} 
                          hover
                          sx={{ 
                            bgcolor: signal.blocked ? 'rgba(255, 152, 0, 0.05)' : 'transparent'
                          }}
                        >
                          <TableCell sx={{ whiteSpace: 'nowrap' }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatDistanceToNow(new Date(signal.snapshot_time), { addSuffix: true })}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>
                              {signal.symbol}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Chip 
                                label={signal.action} 
                                size="small" 
                                sx={{ 
                                  fontSize: 10, 
                                  height: 20,
                                  bgcolor: getActionColor(signal.action) === 'default' ? 'action.disabledBackground' : `status.${getActionColor(signal.action)}`,
                                  color: getActionColor(signal.action) === 'default' ? 'text.secondary' : 'white'
                                }}
                              />
                              {signal.blocked && (
                                <Chip label="BLOCKED" size="small" color="warning" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
                              )}
                            </Stack>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              {signal.signal_price.toLocaleString()}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              {(signal.confidence * 100).toFixed(1)}%
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}
