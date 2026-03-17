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
import {
  formatDateTime,
  formatRelativeTime,
  translateBacktestStatus,
  translateMode,
  translateSessionStatus,
  translateStrategyType,
} from '@/shared/lib/i18n'
import {
  formatBuiltinPluginConfigValue,
  getBuiltinPluginOption,
  getBuiltinPluginSummaryFields,
} from '@/features/strategies/pluginCatalog'

type JsonObject = Record<string, unknown>

function asObject(value: unknown): JsonObject {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as JsonObject) : {}
}

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
        <Typography variant="h5" color="text.secondary" mb={2}>전략을 찾을 수 없습니다</Typography>
        <Button variant="contained" onClick={() => navigate('/strategies')}>전략 목록으로 돌아가기</Button>
      </Box>
    )
  }

  const latestVersion = versions?.[0]
  const strategyVersionIds = new Set((versions ?? []).map((version) => version.id))
  const relatedSessions = (sessions ?? []).filter((session) => strategyVersionIds.has(session.strategy_version_id) && session.status === 'RUNNING')
  const relatedBacktests = (backtests ?? []).filter((run) => strategyVersionIds.has(run.strategy_version_id))
  const latestConfig = latestVersion ? asObject(latestVersion.config_json) : {}
  const pluginId = typeof latestConfig.plugin_id === 'string' ? latestConfig.plugin_id : ''
  const pluginVersion = typeof latestConfig.plugin_version === 'string' ? latestConfig.plugin_version : '-'
  const pluginConfig = asObject(latestConfig.plugin_config)
  const pluginOption = getBuiltinPluginOption(pluginId)
  const pluginSummaryFields = getBuiltinPluginSummaryFields(pluginId)

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
              label={translateStrategyType(strategy.strategy_type)} 
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
              {strategy.is_active ? '활성' : '비활성'}
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
          편집
        </Button>
        <Button 
          variant="contained" 
          color="primary" 
          startIcon={<Play size={16} />}
          onClick={() => navigate('/backtests')}
        >
          백테스트 실행
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          {/* Latest Version Summary */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>최신 버전 요약</Typography>
              {latestVersion ? (
                <Grid container spacing={2}>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">버전</Typography>
                    <Typography variant="body1">v{latestVersion.version_no}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">스키마</Typography>
                    <Typography variant="body1">{latestVersion.schema_version}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">설정 해시</Typography>
                    <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>
                      {latestVersion.config_hash.substring(0, 8)}...
                    </Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">검증 완료</Typography>
                    <Typography variant="body1">{latestVersion.is_validated ? '예' : '아니오'}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={3}>
                    <Typography variant="caption" color="text.tertiary">생성일</Typography>
                    <Typography variant="body1">
                      {formatRelativeTime(latestVersion.created_at)}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Typography variant="caption" color="text.tertiary">라벨</Typography>
                    <Stack direction="row" spacing={1} mt={0.5}>
                      {latestVersion.labels.length > 0 ? (
                        latestVersion.labels.map(label => (
                          <Chip key={label} label={label} size="small" variant="outlined" />
                        ))
                      ) : (
                        <Typography variant="body2" color="text.disabled">없음</Typography>
                      )}
                    </Stack>
                  </Grid>
                  {latestVersion.notes && (
                    <Grid item xs={12}>
                      <Typography variant="caption" color="text.tertiary">노트</Typography>
                      <Typography variant="body2" sx={{ mt: 0.5, p: 1.5, bgcolor: 'bg.surface2', borderRadius: 1 }}>
                        {latestVersion.notes}
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              ) : (
                <Typography color="text.secondary">버전이 없습니다.</Typography>
              )}
            </CardContent>
          </Card>

          {strategy.strategy_type === 'plugin' && latestVersion ? (
            <Card sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6" mb={2}>플러그인 요약</Typography>
                <Stack spacing={2}>
                  <Box>
                    <Stack direction="row" spacing={1} alignItems="center" mb={0.75}>
                      <Typography variant="subtitle1" fontWeight={700}>
                        {(pluginOption?.label ?? pluginId) || '미등록 플러그인'}
                      </Typography>
                      <Chip label={`v${pluginVersion}`} size="small" variant="outlined" />
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      {pluginOption?.description ?? '프런트에 등록된 플러그인 설명이 없어 저장된 plugin_id 기준으로만 표시합니다.'}
                    </Typography>
                  </Box>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="caption" color="text.tertiary">플러그인 ID</Typography>
                      <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>{pluginId || '-'}</Typography>
                    </Grid>
                    {pluginSummaryFields.length > 0 ? pluginSummaryFields.map((field) => (
                      <Grid item xs={12} sm={6} key={field.key}>
                        <Typography variant="caption" color="text.tertiary">{field.label}</Typography>
                        <Typography variant="body1">
                          {formatBuiltinPluginConfigValue(field, pluginConfig[field.key] ?? pluginOption?.defaultConfig[field.key])}
                        </Typography>
                      </Grid>
                    )) : (
                      <Grid item xs={12}>
                        <Typography variant="body2" color="text.secondary">
                          요약용 필드 정의가 없어 plugin_config 원본 값은 JSON 미리보기에서 확인할 수 있습니다.
                        </Typography>
                      </Grid>
                    )}
                  </Grid>
                </Stack>
              </CardContent>
            </Card>
          ) : null}

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
                <Typography variant="h6">설정 JSON</Typography>
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
              <Typography variant="h6" mb={2}>버전 이력</Typography>
            </CardContent>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
                    <TableCell>버전</TableCell>
                    <TableCell>라벨</TableCell>
                    <TableCell>노트</TableCell>
                    <TableCell>생성일</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {versions?.map((v) => (
                    <TableRow key={v.id}>
                      <TableCell>
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography
                            component="span"
                            variant="body2"
                            fontWeight={v.version_no === strategy.latest_version_no ? 600 : 400}
                          >
                            v{v.version_no}
                          </Typography>
                          {v.version_no === strategy.latest_version_no && (
                            <Chip label="최신" size="small" color="primary" sx={{ height: 16, fontSize: 9 }} />
                          )}
                        </Stack>
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
                          {formatDateTime(v.created_at)}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!versions?.length && (
                    <TableRow>
                      <TableCell colSpan={4} align="center" sx={{ py: 3 }}>
                        <Typography color="text.secondary">버전 이력이 없습니다</Typography>
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
              <Typography variant="h6" mb={2}>성과</Typography>
              {strategy.last_7d_return_pct !== null ? (
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.tertiary">최근 7일 수익률</Typography>
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
                    <Typography variant="caption" color="text.tertiary">승률</Typography>
                    <Typography variant="h5" sx={{ fontVariantNumeric: 'tabular-nums' }}>
                      {strategy.last_7d_win_rate !== null ? `${(strategy.last_7d_win_rate * 100).toFixed(1)}%` : '-'}
                    </Typography>
                  </Grid>
                </Grid>
              ) : (
                <Typography color="text.secondary" variant="body2">성과 데이터가 없습니다.</Typography>
              )}
            </CardContent>
          </Card>

          {/* Related Backtests */}
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" mb={2}>최근 백테스트</Typography>
              {relatedBacktests.length === 0 ? (
                <Typography color="text.secondary" variant="body2">이 전략의 백테스트가 없습니다.</Typography>
              ) : (
                <Stack spacing={1.5}>
                  {relatedBacktests.slice(0, 4).map((run) => (
                    <Box key={run.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'bg.surface2' }}>
                      <Typography variant="body2" fontWeight={600}>{run.id.substring(0, 8)}</Typography>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {translateBacktestStatus(run.status)} · 거래 {run.metrics?.trade_count ?? 0}건
                      </Typography>
                      <Typography variant="caption" sx={{ color: (run.metrics?.total_return_pct ?? 0) >= 0 ? 'status.success' : 'status.danger' }}>
                        {(run.metrics?.total_return_pct ?? 0).toFixed(2)}% 수익률
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
              <Typography variant="h6" mb={2}>활성 세션</Typography>
              {relatedSessions.length === 0 ? (
                <Typography color="text.secondary" variant="body2">이 전략의 세션이 없습니다.</Typography>
              ) : (
                <Stack spacing={1.5}>
                  {relatedSessions.slice(0, 4).map((session) => (
                    <Box key={session.id} sx={{ p: 1.5, borderRadius: 1, bgcolor: 'bg.surface2' }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" fontWeight={600}>{session.id.substring(0, 8)}</Typography>
                        <Chip label={translateMode(session.mode)} size="small" variant="outlined" />
                      </Stack>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {translateSessionStatus(session.status)} · 활성 심볼 {(session.symbol_scope.active_symbols ?? []).length}개
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
