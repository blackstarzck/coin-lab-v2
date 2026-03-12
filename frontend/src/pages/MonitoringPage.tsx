import {
  Alert,
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
  Checkbox,
  Skeleton,
  Stack,
  Button,
  Tabs,
  Tab,
  useTheme,
  Divider
} from '@mui/material'
import { Activity, AlertTriangle, StopCircle, RefreshCw } from 'lucide-react'
import {
  useSessions,
  useSession,
  useSessionPositions,
  useSessionOrders,
  useSessionSignals,
  useSessionRiskEvents,
  useStopSession,
  useKillSession,
} from '@/features/sessions/api'
import { useUiStore } from '@/stores/ui-store'
import { CandlestickChart } from '@/shared/charts/CandlestickChart'
import { useChartStream } from '@/features/monitoring/useChartStream'
import { format } from 'date-fns'
import { useEffect, useMemo, useState } from 'react'
import { useLogs } from '@/features/logs/api'

export default function MonitoringPage() {
  const theme = useTheme()
  const { data: sessions, isLoading: isLoadingSessions } = useSessions()
  
  const { 
    selectedSessionId, 
    setSelectedSession, 
    selectedCompareSessionIds,
    setCompareSessionIds,
    selectedSymbol, 
    setSelectedSymbol,
    chartTimeframe,
    setChartTimeframe,
    chartOverlays,
    toggleChartOverlay
  } = useUiStore()

  const activeSessionId = selectedSessionId || sessions?.[0]?.id || ''
  const { data: session } = useSession(activeSessionId)
  const { data: positions } = useSessionPositions(activeSessionId)
  const { data: orders } = useSessionOrders(activeSessionId)
  const { data: signals } = useSessionSignals(activeSessionId)
  const { data: riskEvents } = useSessionRiskEvents(activeSessionId)
  const { data: eventLogs } = useLogs('strategy-execution', activeSessionId)
  const stopSession = useStopSession()
  const killSession = useKillSession()

  const availableSymbols = useMemo(
    () => session?.symbol_scope?.active_symbols || [],
    [session?.symbol_scope?.active_symbols],
  )
  const activeSymbol = selectedSymbol && availableSymbols.includes(selectedSymbol)
    ? selectedSymbol
    : availableSymbols[0] || null

  const { data: chartData, isConnected } = useChartStream(activeSymbol, chartTimeframe)

  const [rightTab, setRightTab] = useState(0)
  const [bottomTab, setBottomTab] = useState(0)

  useEffect(() => {
    if (!selectedSessionId && sessions?.[0]?.id) {
      setSelectedSession(sessions[0].id)
    }
  }, [selectedSessionId, sessions, setSelectedSession])

  useEffect(() => {
    if (!selectedSymbol && availableSymbols[0]) {
      setSelectedSymbol(availableSymbols[0])
    }
  }, [availableSymbols, selectedSymbol, setSelectedSymbol])

  const compareSessions = useMemo(
    () => (sessions ?? []).filter((item) => selectedCompareSessionIds.includes(item.id)),
    [selectedCompareSessionIds, sessions],
  )

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

  const getActionColor = (action: string) => {
    return action === 'ENTER' ? 'success' : 'error'
  }

  const getOrderStateColor = (state: string) => {
    switch (state) {
      case 'FILLED': return 'success'
      case 'REJECTED': return 'error'
      case 'FAILED': return 'error'
      case 'CANCELLED': return 'default'
      case 'SUBMITTED': return 'info'
      case 'CREATED': return 'default'
      default: return 'default'
    }
  }

  const getPositionStateColor = (state: string) => {
    switch (state) {
      case 'OPEN': return 'success'
      case 'CLOSED': return 'default'
      case 'OPENING': return 'info'
      case 'CLOSING': return 'warning'
      case 'FAILED': return 'error'
      default: return 'default'
    }
  }

  const toggleCompareSession = (id: string) => {
    if (selectedCompareSessionIds.includes(id)) {
      setCompareSessionIds(selectedCompareSessionIds.filter((sessionId) => sessionId !== id))
      return
    }
    if (selectedCompareSessionIds.length < 4) {
      setCompareSessionIds([...selectedCompareSessionIds, id])
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', p: 2, gap: 2 }}>
      {/* Top Global Bar */}
      <Card sx={{ flexShrink: 0 }}>
        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 }, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Typography variant="h6" sx={{ mr: 2 }}>Monitoring</Typography>
            {session ? (
              <>
                <Chip 
                  label={session.mode} 
                  size="small" 
                  sx={{ 
                    bgcolor: getModeColor(session.mode) === 'default' ? 'action.disabledBackground' : `status.${getModeColor(session.mode)}`,
                    color: getModeColor(session.mode) === 'default' ? 'text.secondary' : 'white'
                  }} 
                />
                <Chip 
                  label={session.status} 
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
                  Strategy v{session.strategy_version_id.split('-')[0]}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {session.started_at ? format(new Date(session.started_at), 'MM-dd HH:mm:ss') : 'Not started'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Compare {compareSessions.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Symbols {availableSymbols.length}
                </Typography>
                {session.health && (
                  <Chip 
                    label={session.health.connection_state} 
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
                  <Chip label="LIVE SAFETY ACTIVE" size="small" color="error" />
                ) : null}
              </>
            ) : (
              <Typography color="text.secondary" variant="body2">No session selected</Typography>
            )}
          </Stack>
          
          <Stack direction="row" spacing={1}>
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
              Stop
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
              Emergency Kill
            </Button>
          </Stack>
        </CardContent>
      </Card>
      
      {/* 3-Column Layout */}
      <Box sx={{ display: 'flex', flexGrow: 1, gap: 2, minHeight: 0 }}>
        
        {/* Left Panel - Sessions & Universe */}
        <Card sx={{ width: 280, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>SESSIONS</Typography>
            <Stack spacing={1} sx={{ maxHeight: 200, overflowY: 'auto' }}>
              {isLoadingSessions ? (
                <Skeleton variant="rounded" height={40} />
              ) : sessions?.length === 0 ? (
                <Typography variant="body2" color="text.secondary">No active sessions</Typography>
              ) : (
                sessions?.map(s => (
                  <Box 
                    key={s.id}
                    onClick={() => setSelectedSession(s.id)}
                    sx={{ 
                      p: 1, 
                      borderRadius: 1, 
                      cursor: 'pointer',
                      border: 1,
                      borderColor: activeSessionId === s.id ? 'primary.main' : 'divider',
                      bgcolor: activeSessionId === s.id ? 'rgba(34, 231, 107, 0.05)' : 'transparent',
                      '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' }
                    }}
                  >
                    <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
                      <Typography variant="body2" fontFamily="monospace">{s.id.split('-')[0]}</Typography>
                      <Chip 
                        label={s.mode} 
                        size="small" 
                        sx={{ 
                          fontSize: 10, 
                          height: 16,
                          bgcolor: getModeColor(s.mode) === 'default' ? 'action.disabledBackground' : `status.${getModeColor(s.mode)}`,
                          color: getModeColor(s.mode) === 'default' ? 'text.secondary' : 'white'
                        }} 
                      />
                    </Stack>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="caption" color="text.secondary">v{s.strategy_version_id.split('-')[0]}</Typography>
                      <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: getStatusColor(s.status) === 'default' ? 'text.disabled' : `status.${getStatusColor(s.status)}` }} />
                    </Stack>
                  </Box>
                ))
              )}
            </Stack>
          </Box>

          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>COMPARE</Typography>
            <Stack spacing={0.5}>
              {(sessions ?? []).slice(0, 4).map((compareSession) => (
                <Box key={compareSession.id} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Checkbox
                      size="small"
                      checked={selectedCompareSessionIds.includes(compareSession.id)}
                      onChange={() => toggleCompareSession(compareSession.id)}
                      disabled={!selectedCompareSessionIds.includes(compareSession.id) && selectedCompareSessionIds.length >= 4}
                    />
                    <Box>
                      <Typography variant="caption" fontWeight={600}>{compareSession.id.split('-')[0]}</Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {compareSession.performance?.realized_pnl_pct?.toFixed(2) ?? '0.00'}%
                      </Typography>
                    </Box>
                  </Stack>
                  <Chip label={compareSession.mode} size="small" variant="outlined" sx={{ height: 18, fontSize: 10 }} />
                </Box>
              ))}
            </Stack>
          </Box>
          
          <Box sx={{ p: 2, flexGrow: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>ACTIVE UNIVERSE</Typography>
            <Box sx={{ overflowY: 'auto', flexGrow: 1 }}>
              {!session ? (
                <Typography variant="body2" color="text.secondary">Select a session</Typography>
              ) : !session.symbol_scope?.active_symbols?.length ? (
                <Typography variant="body2" color="text.secondary">No active symbols</Typography>
              ) : (
                <Stack spacing={0.5}>
                  {session.symbol_scope.active_symbols.map(sym => (
                    <Box 
                      key={sym}
                      onClick={() => setSelectedSymbol(sym)}
                      sx={{ 
                        p: 1, 
                        borderRadius: 1, 
                        cursor: 'pointer',
                        bgcolor: activeSymbol === sym ? 'rgba(255,255,255,0.05)' : 'transparent',
                        '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' },
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <Typography variant="body2" fontWeight={activeSymbol === sym ? 600 : 400}>{sym}</Typography>
                      {activeSymbol === sym && <Activity size={14} color={theme.palette.primary.main} />}
                    </Box>
                  ))}
                </Stack>
              )}
            </Box>
          </Box>
        </Card>

        {/* Center Panel - Chart */}
        <Card sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <Box sx={{ p: 1.5, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="subtitle1" fontWeight={600}>
                {activeSymbol || 'No Symbol Selected'}
              </Typography>
              {isConnected && (
                <Chip icon={<RefreshCw size={12} />} label="Live" size="small" color="success" variant="outlined" sx={{ height: 20, fontSize: 10 }} />
              )}
            </Stack>
            
            <Stack direction="row" spacing={2} alignItems="center">
              <Stack direction="row" spacing={0.5}>
                {['1m', '5m', '15m', '1h'].map(tf => (
                  <Button 
                    key={tf}
                    size="small" 
                    variant={chartTimeframe === tf ? 'contained' : 'text'} 
                    color={chartTimeframe === tf ? 'primary' : 'inherit'}
                    onClick={() => setChartTimeframe(tf)}
                    sx={{ minWidth: 0, px: 1, py: 0.5 }}
                  >
                    {tf}
                  </Button>
                ))}
              </Stack>
              <Divider orientation="vertical" flexItem />
              <Stack direction="row" spacing={0.5}>
                <Chip 
                  label="MA" 
                  size="small" 
                  variant={chartOverlays.ma ? 'filled' : 'outlined'} 
                  onClick={() => toggleChartOverlay('ma')}
                  sx={{ cursor: 'pointer' }}
                />
                <Chip 
                  label="Vol" 
                  size="small" 
                  variant={chartOverlays.volume ? 'filled' : 'outlined'} 
                  onClick={() => toggleChartOverlay('volume')}
                  sx={{ cursor: 'pointer' }}
                />
                <Chip 
                  label="Signals" 
                  size="small" 
                  variant={chartOverlays.signalMarkers ? 'filled' : 'outlined'} 
                  onClick={() => toggleChartOverlay('signalMarkers')}
                  sx={{ cursor: 'pointer' }}
                />
              </Stack>
            </Stack>
          </Box>
          
          <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
            {!activeSymbol ? (
              <Typography color="text.secondary">Select a session and symbol to view chart</Typography>
            ) : chartData?.candles?.length ? (
              <CandlestickChart data={chartData.candles} height={400} />
            ) : (
              <Box sx={{ textAlign: 'center' }}>
                <Activity size={32} color={theme.palette.text.disabled} style={{ marginBottom: 8 }} />
                <Typography color="text.secondary">Waiting for chart data...</Typography>
              </Box>
            )}
          </Box>
        </Card>

        {/* Right Panel - Signals/Positions/Orders */}
        <Card sx={{ width: 360, display: 'flex', flexDirection: 'column', flexShrink: 0 }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={rightTab} onChange={(_, v) => setRightTab(v)} variant="fullWidth" sx={{ minHeight: 40 }}>
              <Tab label="Signals" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="Positions" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="Orders" sx={{ minHeight: 40, py: 1 }} />
              <Tab label="Risk" sx={{ minHeight: 40, py: 1 }} />
            </Tabs>
          </Box>
          
          <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
            {rightTab === 0 && (
              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1, px: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>Time</TableCell>
                      <TableCell>Sym</TableCell>
                      <TableCell>Action</TableCell>
                      <TableCell align="right">Price</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!signals?.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography variant="body2" color="text.secondary">No signals</Typography></TableCell></TableRow>
                    ) : (
                      signals.map(sig => {
                        const actionColor = getActionColor(sig.action)
                        return (
                          <TableRow key={sig.id} hover sx={{ bgcolor: sig.blocked ? 'rgba(255, 152, 0, 0.05)' : 'transparent' }}>
                            <TableCell sx={{ whiteSpace: 'nowrap' }}><Typography variant="caption" color="text.secondary">{format(new Date(sig.snapshot_time), 'HH:mm:ss')}</Typography></TableCell>
                            <TableCell><Typography variant="caption" fontWeight={600}>{sig.symbol}</Typography></TableCell>
                            <TableCell>
                              <Chip 
                                label={sig.action} 
                                size="small" 
                                sx={{ 
                                  fontSize: 9, 
                                  height: 16,
                                  bgcolor: `status.${actionColor}`,
                                  color: 'white'
                                }} 
                              />
                              {sig.blocked && <Chip label="BLK" size="small" color="warning" variant="outlined" sx={{ fontSize: 9, height: 16, ml: 0.5 }} />}
                            </TableCell>
                            <TableCell align="right"><Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums' }}>{sig.signal_price.toLocaleString()}</Typography></TableCell>
                          </TableRow>
                        )
                      })
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
            
            {rightTab === 1 && (
              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1, px: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>Sym</TableCell>
                      <TableCell align="right">Qty</TableCell>
                      <TableCell align="right">Entry</TableCell>
                      <TableCell align="right">PnL</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!positions?.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography variant="body2" color="text.secondary">No positions</Typography></TableCell></TableRow>
                    ) : (
                      positions.map(pos => (
                        <TableRow key={pos.id} hover>
                          <TableCell>
                            <Typography variant="caption" fontWeight={600} display="block">{pos.symbol}</Typography>
                            <Chip 
                              label={pos.position_state} 
                              size="small" 
                              sx={{ 
                                fontSize: 9, 
                                height: 16,
                                bgcolor: getPositionStateColor(pos.position_state) === 'default' ? 'action.disabledBackground' : `status.${getPositionStateColor(pos.position_state)}`,
                                color: getPositionStateColor(pos.position_state) === 'default' ? 'text.secondary' : 'white'
                              }} 
                            />
                          </TableCell>
                          <TableCell align="right"><Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums' }}>{pos.quantity}</Typography></TableCell>
                          <TableCell align="right"><Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums' }}>{pos.avg_entry_price.toLocaleString()}</Typography></TableCell>
                          <TableCell align="right">
                            <Typography variant="caption" sx={{ color: pos.unrealized_pnl >= 0 ? 'status.success' : 'status.danger', fontVariantNumeric: 'tabular-nums', display: 'block' }}>
                              {pos.unrealized_pnl > 0 ? '+' : ''}{pos.unrealized_pnl.toLocaleString()}
                            </Typography>
                            <Typography variant="caption" sx={{ color: pos.unrealized_pnl_pct >= 0 ? 'status.success' : 'status.danger', fontVariantNumeric: 'tabular-nums' }}>
                              {pos.unrealized_pnl_pct > 0 ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {rightTab === 2 && (
              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1, px: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>Time</TableCell>
                      <TableCell>Sym</TableCell>
                      <TableCell>Type</TableCell>
                      <TableCell align="right">Price</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!orders?.length ? (
                      <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography variant="body2" color="text.secondary">No orders</Typography></TableCell></TableRow>
                    ) : (
                      orders.map(ord => (
                        <TableRow key={ord.id} hover>
                          <TableCell sx={{ whiteSpace: 'nowrap' }}><Typography variant="caption" color="text.secondary">{format(new Date(ord.submitted_at), 'HH:mm:ss')}</Typography></TableCell>
                          <TableCell><Typography variant="caption" fontWeight={600}>{ord.symbol}</Typography></TableCell>
                          <TableCell>
                            <Typography variant="caption" display="block">{ord.order_type}</Typography>
                            <Chip 
                              label={ord.order_state} 
                              size="small" 
                              sx={{ 
                                fontSize: 9, 
                                height: 16,
                                bgcolor: getOrderStateColor(ord.order_state) === 'default' ? 'action.disabledBackground' : `status.${getOrderStateColor(ord.order_state)}`,
                                color: getOrderStateColor(ord.order_state) === 'default' ? 'text.secondary' : 'white'
                              }} 
                            />
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums', display: 'block' }}>
                              {ord.executed_price ? ord.executed_price.toLocaleString() : (ord.requested_price ? ord.requested_price.toLocaleString() : 'MKT')}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                              {ord.executed_qty}/{ord.requested_qty}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}

            {rightTab === 3 && (
              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1, px: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                      <TableCell>Time</TableCell>
                      <TableCell>Code</TableCell>
                      <TableCell>Severity</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {!riskEvents?.length ? (
                      <TableRow><TableCell colSpan={3} align="center" sx={{ py: 4 }}><Typography variant="body2" color="text.secondary">No risk events</Typography></TableCell></TableRow>
                    ) : (
                      riskEvents.map((event) => (
                        <TableRow key={event.id} hover>
                          <TableCell><Typography variant="caption" color="text.secondary">{format(new Date(event.created_at), 'HH:mm:ss')}</Typography></TableCell>
                          <TableCell><Typography variant="caption" fontFamily="monospace">{event.code}</Typography></TableCell>
                          <TableCell><Chip label={event.severity} size="small" color={event.severity === 'WARN' ? 'warning' : 'error'} /></TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        </Card>
      </Box>

      {/* Bottom Tabs */}
      <Card sx={{ height: 200, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={bottomTab} onChange={(_, v) => setBottomTab(v)} sx={{ minHeight: 40 }}>
            <Tab label="Event Log" sx={{ minHeight: 40, py: 1 }} />
            <Tab label="Strategy Explain" sx={{ minHeight: 40, py: 1 }} />
            <Tab label="Order Timeline" sx={{ minHeight: 40, py: 1 }} />
            <Tab label="Risk Events" sx={{ minHeight: 40, py: 1 }} />
          </Tabs>
        </Box>
        <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
          {bottomTab === 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                    <TableCell>Time</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Message</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {!eventLogs?.length ? (
                    <TableRow><TableCell colSpan={3} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No event logs</Typography></TableCell></TableRow>
                  ) : (
                    eventLogs.slice(0, 20).map((log) => (
                      <TableRow key={log.id} hover>
                        <TableCell><Typography variant="caption" color="text.secondary">{format(new Date(log.timestamp), 'HH:mm:ss')}</Typography></TableCell>
                        <TableCell><Typography variant="caption" fontFamily="monospace">{log.event_type ?? '-'}</Typography></TableCell>
                        <TableCell><Typography variant="caption">{log.message}</Typography></TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}

          {bottomTab === 1 ? (
            <Stack spacing={1.5} sx={{ p: 2 }}>
              {!signals?.length ? (
                <Typography color="text.secondary">No signals yet.</Typography>
              ) : (
                signals.slice(0, 5).map((signal) => (
                  <Card key={signal.id} variant="outlined">
                    <Box sx={{ p: 1.5 }}>
                      <Typography variant="body2" fontWeight={600}>{signal.symbol} · {signal.action}</Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {signal.reason_codes.join(', ') || 'No explain facts'}
                      </Typography>
                    </Box>
                  </Card>
                ))
              )}
            </Stack>
          ) : null}

          {bottomTab === 2 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 11 } }}>
                    <TableCell>Time</TableCell>
                    <TableCell>Role</TableCell>
                    <TableCell>State</TableCell>
                    <TableCell align="right">Qty</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {!orders?.length ? (
                    <TableRow><TableCell colSpan={4} align="center" sx={{ py: 4 }}><Typography color="text.secondary">No orders</Typography></TableCell></TableRow>
                  ) : (
                    orders.map((order) => (
                      <TableRow key={order.id} hover>
                        <TableCell><Typography variant="caption" color="text.secondary">{format(new Date(order.submitted_at), 'HH:mm:ss')}</Typography></TableCell>
                        <TableCell><Typography variant="caption">{order.order_role}</Typography></TableCell>
                        <TableCell><Typography variant="caption">{order.order_state}</Typography></TableCell>
                        <TableCell align="right"><Typography variant="caption">{order.executed_qty}/{order.requested_qty}</Typography></TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          ) : null}

          {bottomTab === 3 ? (
            <Stack spacing={1.5} sx={{ p: 2 }}>
              {!riskEvents?.length ? (
                <Typography color="text.secondary">No risk events.</Typography>
              ) : (
                riskEvents.map((event) => (
                  <Alert key={event.id} severity={event.severity === 'WARN' ? 'warning' : 'error'}>
                    [{event.code}] {event.message}
                  </Alert>
                ))
              )}
            </Stack>
          ) : null}
        </Box>
      </Card>
    </Box>
  )
}
