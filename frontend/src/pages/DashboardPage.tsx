import { type ReactNode, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  ButtonBase,
  Card,
  CardContent,
  Chip,
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
import { Activity, AlertTriangle, CheckCircle2, Clock, PlayCircle, Radio, XCircle } from 'lucide-react'
import { useMonitoringSummary } from '@/features/monitoring/api'
import { useMonitoringSummaryStream } from '@/features/monitoring/useMonitoringSummaryStream'
import { formatRelativeTime, formatTime, translateSeverity, translateSignalAction, translateStrategyType } from '@/shared/lib/i18n'
import { AnimatedOdometer } from '@/shared/ui/AnimatedOdometer'
import { StatusText } from '@/shared/ui/StatusText'
import { useAnimatedTableRows } from '@/shared/ui/useAnimatedTableRows'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data: summary, isLoading } = useMonitoringSummary()
  const { isConnected } = useMonitoringSummaryStream()

  const totalRealizedPnl = useMemo(() => {
    const returns = summary?.strategy_cards
      ?.map((card) => card.last_7d_return_pct)
      .filter((value): value is number => value !== null)

    if (!returns?.length) {
      return null
    }

    return returns.reduce((sum, value) => sum + value, 0)
  }, [summary?.strategy_cards])

  const riskRowIds = useMemo(
    () => summary?.risk_overview.items.map((item) => item.id) ?? [],
    [summary?.risk_overview.items],
  )
  const signalRowIds = useMemo(
    () => summary?.recent_signals.map((item) => item.id) ?? [],
    [summary?.recent_signals],
  )
  const { setRowRef: setRiskRowRef } = useAnimatedTableRows(riskRowIds)
  const { setRowRef: setSignalRowRef } = useAnimatedTableRows(signalRowIds)

  const getSeverityColor = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'HIGH':
        return 'error'
      case 'MEDIUM':
        return 'warning'
      case 'LOW':
        return 'info'
      default:
        return 'default'
    }
  }

  const getActionTone = (action: string) => (action === 'ENTER' ? 'success' : 'danger')

  if (isLoading && summary === undefined) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h4" sx={{ mb: 3 }}>
          대시보드
        </Typography>
        <Grid container spacing={2} sx={{ mb: 4 }}>
          {Array.from({ length: 4 }).map((_, index) => (
            <Grid item xs={12} sm={6} md={3} key={index}>
              <Skeleton variant="rounded" height={112} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {Array.from({ length: 2 }).map((_, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Skeleton variant="rounded" height={240} />
            </Grid>
          ))}
        </Grid>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rounded" height={420} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Skeleton variant="rounded" height={420} />
          </Grid>
        </Grid>
      </Box>
    )
  }

  const statusBar = summary?.status_bar
  const strategyCards = summary?.strategy_cards ?? []
  const activeStrategyCards = strategyCards.filter((strategy) => strategy.active_session_count > 0)
  const riskItems = summary?.risk_overview.items ?? []
  const recentSignals = summary?.recent_signals ?? []

  return (
    <Box sx={{ p: 3 }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1.5}
        alignItems={{ xs: 'flex-start', sm: 'center' }}
        justifyContent="space-between"
        sx={{ mb: 3 }}
      >
        <Typography variant="h4">대시보드</Typography>
        <Chip
          icon={<Radio size={14} />}
          label={isConnected ? '실시간 연결' : '재연결 중'}
          color={isConnected ? 'success' : 'warning'}
          variant="outlined"
        />
      </Stack>

      <Stack direction="row" spacing={2} sx={{ mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Chip icon={<PlayCircle size={16} />} label={`실행 중 ${statusBar?.running_session_count ?? 0}개`} color="success" variant="outlined" />
        <Chip icon={<Activity size={16} />} label={`모의 ${statusBar?.paper_session_count ?? 0}개`} color="info" variant="outlined" />
        <Chip icon={<Activity size={16} />} label={`실전 ${statusBar?.live_session_count ?? 0}개`} color="error" variant="outlined" />
        <Chip icon={<XCircle size={16} />} label={`실패 ${statusBar?.failed_session_count ?? 0}개`} color="error" variant="outlined" />
        <Chip icon={<AlertTriangle size={16} />} label={`성능 저하 ${statusBar?.degraded_session_count ?? 0}개`} color="warning" variant="outlined" />
        <Chip icon={<CheckCircle2 size={16} />} label={`활성 심볼 ${statusBar?.active_symbol_count ?? 0}개`} color="default" variant="outlined" />
      </Stack>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="실행 중 세션"
            color="text.primary"
            value={<AnimatedOdometer value={statusBar?.running_session_count ?? 0} />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="활성 심볼"
            color="text.primary"
            value={<AnimatedOdometer value={statusBar?.active_symbol_count ?? 0} />}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="최근 7일 수익률 합계"
            color={totalRealizedPnl === null ? 'text.disabled' : totalRealizedPnl >= 0 ? 'status.success' : 'status.danger'}
            value={
              totalRealizedPnl === null ? (
                <Typography variant="body2" color="text.disabled">
                  데이터 없음
                </Typography>
              ) : (
                <AnimatedOdometer value={totalRealizedPnl} precision={2} suffix="%" showPositiveSign />
              )
            }
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <MetricCard
            label="리스크 알림"
            color={(summary?.risk_overview.active_alert_count ?? 0) > 0 ? 'status.danger' : 'text.primary'}
            value={<AnimatedOdometer value={summary?.risk_overview.active_alert_count ?? 0} />}
          />
        </Grid>
      </Grid>

      <Typography variant="h6" sx={{ mb: 2 }}>
        활성 전략
      </Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {activeStrategyCards.length === 0 ? (
          <Grid item xs={12}>
            <Card>
              <CardContent sx={{ py: 4, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  활성 전략이 없습니다. 세션을 시작하면 여기에 데이터가 표시됩니다.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ) : (
          activeStrategyCards.map((strategy) => (
            <Grid item xs={12} sm={6} md={4} lg={3} key={strategy.strategy_id}>
              <ButtonBase
                onClick={() => navigate(`/strategies/${strategy.strategy_id}`)}
                sx={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  borderRadius: 3,
                }}
              >
                <Card
                  sx={{
                    width: '100%',
                    transition: 'transform 180ms ease, box-shadow 180ms ease',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: 6,
                    },
                  }}
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
                          mt: 1,
                        }}
                      />
                    </Box>

                    <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                      <Chip
                        label={translateStrategyType(strategy.strategy_type)}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: 10, height: 20 }}
                      />
                      <Chip
                        icon={<PlayCircle size={12} />}
                        label={`${strategy.active_session_count}개 세션`}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: 10, height: 20 }}
                      />
                    </Stack>

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 2 }}>
                      <Box>
                        <Typography variant="caption" color="text.secondary" display="block">
                          최근 7일 수익률
                        </Typography>
                        {strategy.last_7d_return_pct === null ? (
                          <Typography variant="body2" color="text.disabled">
                            데이터 없음
                          </Typography>
                        ) : (
                          <Box
                            sx={{
                              mt: 0.5,
                              fontSize: '1.05rem',
                              fontWeight: 700,
                              color: strategy.last_7d_return_pct >= 0 ? 'status.success' : 'status.danger',
                            }}
                          >
                            <AnimatedOdometer
                              value={strategy.last_7d_return_pct}
                              precision={2}
                              suffix="%"
                              showPositiveSign
                            />
                          </Box>
                        )}
                      </Box>
                      <Box sx={{ textAlign: 'right' }}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          마지막 신호
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.primary"
                          sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}
                        >
                          <Clock size={12} />
                          {strategy.last_signal_at ? formatRelativeTime(strategy.last_signal_at) : '없음'}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </ButtonBase>
            </Grid>
          ))
        )}
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', minHeight: 420 }}>
            <CardContent sx={{ p: 0 }}>
              <Box
                sx={{
                  p: 2,
                  borderBottom: 1,
                  borderColor: 'divider',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Typography variant="h6">리스크 알림</Typography>
                {summary?.risk_overview.blocked_signal_count_1h ? (
                  <Chip label={`1시간 차단 ${summary.risk_overview.blocked_signal_count_1h}건`} size="small" color="warning" />
                ) : null}
              </Box>

              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
                      <TableCell>시간</TableCell>
                      <TableCell>심각도</TableCell>
                      <TableCell>코드</TableCell>
                      <TableCell>메시지</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {riskItems.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={4} align="center" sx={{ py: 8 }}>
                          <Typography color="text.secondary">활성 리스크 알림이 없습니다.</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      riskItems.map((alert) => (
                        <TableRow
                          key={alert.id}
                          ref={setRiskRowRef(alert.id)}
                          hover
                          sx={{ '& td': { backgroundColor: 'transparent' } }}
                        >
                          <TableCell sx={{ whiteSpace: 'nowrap' }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatTime(alert.created_at)}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={translateSeverity(alert.severity)}
                              size="small"
                              sx={{
                                fontSize: 10,
                                height: 20,
                                bgcolor:
                                  getSeverityColor(alert.severity) === 'default'
                                    ? 'action.disabledBackground'
                                    : `status.${getSeverityColor(alert.severity)}`,
                                color: getSeverityColor(alert.severity) === 'default' ? 'text.secondary' : 'white',
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Typography variant="caption" fontFamily="monospace">
                              {alert.code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" noWrap title={alert.message} sx={{ maxWidth: 240 }}>
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

        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', minHeight: 420 }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="h6">최근 신호</Typography>
              </Box>

              <TableContainer>
                <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1.5 } }}>
                  <TableHead>
                    <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
                      <TableCell>시간</TableCell>
                      <TableCell>심볼</TableCell>
                      <TableCell>액션</TableCell>
                      <TableCell align="right">가격</TableCell>
                      <TableCell align="right">신뢰도</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {recentSignals.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ py: 8 }}>
                          <Typography color="text.secondary">최근 신호가 없습니다.</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      recentSignals.map((signal) => {
                        const actionTone = getActionTone(signal.action)
                        return (
                          <TableRow
                            key={signal.id}
                            ref={setSignalRowRef(signal.id)}
                            hover
                            sx={{
                              bgcolor: signal.blocked ? 'rgba(255, 152, 0, 0.05)' : 'transparent',
                              '& td': { backgroundColor: 'transparent' },
                            }}
                          >
                            <TableCell sx={{ whiteSpace: 'nowrap' }}>
                              <Typography variant="caption" color="text.secondary">
                                {formatRelativeTime(signal.snapshot_time)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontWeight={600}>
                                {signal.symbol}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap">
                                <StatusText tone={actionTone} variant="body2">
                                  {translateSignalAction(signal.action)}
                                </StatusText>
                                {signal.blocked ? (
                                  <StatusText tone="warning">
                                    차단
                                  </StatusText>
                                ) : null}
                              </Stack>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                                {signal.signal_price?.toLocaleString() ?? '-'}
                              </Typography>
                            </TableCell>
                            <TableCell align="right">
                              <Typography variant="body2" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                                {(signal.confidence * 100).toFixed(1)}%
                              </Typography>
                            </TableCell>
                          </TableRow>
                        )
                      })
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

function MetricCard({
  label,
  value,
  color,
}: {
  label: string
  value: ReactNode
  color: string
}) {
  return (
    <Card>
      <CardContent>
        <Typography color="text.secondary" gutterBottom variant="body2">
          {label}
        </Typography>
        <Box
          sx={{
            color,
            fontSize: '2.125rem',
            lineHeight: 1.2,
            fontWeight: 500,
            fontVariantNumeric: 'tabular-nums',
          }}
        >
          {value}
        </Box>
      </CardContent>
    </Card>
  )
}
