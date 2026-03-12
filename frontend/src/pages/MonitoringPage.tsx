import { useMemo } from 'react'
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
  Button,
  IconButton,
  Tabs,
  Tab,
  useTheme,
  Divider
} from '@mui/material'
import { Activity, AlertTriangle, PlayCircle, StopCircle, XCircle, Settings2, RefreshCw } from 'lucide-react'
import { useSessions, useSession, useSessionPositions, useSessionOrders, useSessionSignals } from '@/features/sessions/api'
import { useUiStore } from '@/stores/ui-store'
import { CandlestickChart } from '@/shared/charts/CandlestickChart'
import { useChartStream } from '@/features/monitoring/useChartStream'
import { formatDistanceToNow, format } from 'date-fns'
import { useState } from 'react'

export default function MonitoringPage() {
  const theme = useTheme()
  const { data: sessions, isLoading: isLoadingSessions } = useSessions()
  
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

  const { data: session, isLoading: isLoadingSession } = useSession(selectedSessionId || '')
  const { data: positions } = useSessionPositions(selectedSessionId || '')
  const { data: orders } = useSessionOrders(selectedSessionId || '')
  const { data: signals } = useSessionSignals(selectedSessionId || '')

  const { data: chartData, isConnected } = useChartStream(selectedSymbol)

  const [rightTab, setRightTab] = useState(0)
  const [bottomTab, setBottomTab] = useState(0)

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
            >
              Stop
            </Button>
            <Button 
              variant="contained" 
              color="error" 
              startIcon={<AlertTriangle size={16} />}
              disabled={!session || session.status !== 'RUNNING'}
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
                      borderColor: selectedSessionId === s.id ? 'primary.main' : 'divider',
                      bgcolor: selectedSessionId === s.id ? 'rgba(34, 231, 107, 0.05)' : 'transparent',
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
                        bgcolor: selectedSymbol === sym ? 'rgba(255,255,255,0.05)' : 'transparent',
                        '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' },
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <Typography variant="body2" fontWeight={selectedSymbol === sym ? 600 : 400}>{sym}</Typography>
                      {selectedSymbol === sym && <Activity size={14} color={theme.palette.primary.main} />}
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
                {selectedSymbol || 'No Symbol Selected'}
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
            {!selectedSymbol ? (
              <Typography color="text.secondary">Select a session and symbol to view chart</Typography>
            ) : chartData ? (
              <CandlestickChart data={[]} height={400} /> // Placeholder for actual data
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
                      signals.map(sig => (
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
                                bgcolor: getActionColor(sig.action) === 'default' ? 'action.disabledBackground' : `status.${getActionColor(sig.action)}`,
                                color: getActionColor(sig.action) === 'default' ? 'text.secondary' : 'white'
                              }} 
                            />
                            {sig.blocked && <Chip label="BLK" size="small" color="warning" variant="outlined" sx={{ fontSize: 9, height: 16, ml: 0.5 }} />}
                          </TableCell>
                          <TableCell align="right"><Typography variant="caption" sx={{ fontVariantNumeric: 'tabular-nums' }}>{sig.signal_price.toLocaleString()}</Typography></TableCell>
                        </TableRow>
                      ))
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
              <Box sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="body2" color="text.secondary">Risk events will appear here</Typography>
              </Box>
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
        <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Typography color="text.secondary">Select a tab to view details</Typography>
        </Box>
      </Card>
    </Box>
  )
}
