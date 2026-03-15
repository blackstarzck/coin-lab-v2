import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
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
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  FormControlLabel,
  Switch,
  Chip,
  IconButton,
  Skeleton,
  Stack,
  Tooltip,
} from '@mui/material'
import type { ChipProps } from '@mui/material'
import { Eye, Edit2, Play, Activity } from 'lucide-react'
import { useStrategies } from '@/features/strategies/api'
import { formatRelativeTime, translateStrategyType } from '@/shared/lib/i18n'

export default function StrategiesPage() {
  const navigate = useNavigate()
  const { data: strategies, isLoading } = useStrategies()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [activeOnly, setActiveOnly] = useState(false)

  const filteredStrategies = useMemo(() => {
    if (!strategies) return []
    return strategies.filter((s) => {
      if (search && !s.name.toLowerCase().includes(search.toLowerCase()) && !s.strategy_key.toLowerCase().includes(search.toLowerCase())) {
        return false
      }
      if (typeFilter !== 'all' && s.strategy_type !== typeFilter) {
        return false
      }
      if (activeOnly && !s.is_active) {
        return false
      }
      return true
    })
  }, [strategies, search, typeFilter, activeOnly])

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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">전략</Typography>
        <Button variant="contained" color="primary" onClick={() => navigate('/strategies/new')}>전략 생성</Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField
            size="small"
            placeholder="이름 또는 키로 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>유형</InputLabel>
            <Select
              value={typeFilter}
              label="유형"
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <MenuItem value="all">전체</MenuItem>
              <MenuItem value="dsl">DSL</MenuItem>
              <MenuItem value="plugin">플러그인</MenuItem>
              <MenuItem value="hybrid">하이브리드</MenuItem>
            </Select>
          </FormControl>
          <FormControlLabel
            control={<Switch checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} />}
            label="활성 전략만"
          />
        </CardContent>
      </Card>

      <TableContainer component={Card} sx={{ borderRadius: 2 }}>
        <Table size="small" sx={{ '& .MuiTableCell-root': { py: 1.5 } }}>
          <TableHead>
            <TableRow sx={{ '& .MuiTableCell-head': { color: 'text.tertiary', fontSize: 12 } }}>
              <TableCell>전략명</TableCell>
              <TableCell>최신 버전</TableCell>
              <TableCell>유형</TableCell>
              <TableCell>태그</TableCell>
              <TableCell>활성</TableCell>
              <TableCell align="right">최근 7일 수익률</TableCell>
              <TableCell>업데이트</TableCell>
              <TableCell align="right">작업</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              Array.from(new Array(5)).map((_, i) => (
                <TableRow key={i}>
                  <TableCell><Skeleton width={120} /></TableCell>
                  <TableCell><Skeleton width={40} /></TableCell>
                  <TableCell><Skeleton width={60} /></TableCell>
                  <TableCell><Skeleton width={100} /></TableCell>
                  <TableCell><Skeleton variant="circular" width={12} height={12} /></TableCell>
                  <TableCell align="right"><Skeleton width={60} sx={{ ml: 'auto' }} /></TableCell>
                  <TableCell><Skeleton width={80} /></TableCell>
                  <TableCell align="right"><Skeleton width={100} sx={{ ml: 'auto' }} /></TableCell>
                </TableRow>
              ))
            ) : filteredStrategies.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center" sx={{ py: 8 }}>
                  <Typography color="text.secondary" mb={2}>전략이 없습니다. 첫 전략을 만들어 시작하세요.</Typography>
                  <Button variant="outlined" color="primary" onClick={() => navigate('/strategies/new')}>전략 생성</Button>
                </TableCell>
              </TableRow>
            ) : (
              filteredStrategies.map((strategy) => (
                <TableRow 
                  key={strategy.id} 
                  hover 
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'rgba(255,255,255,0.02)' }
                  }}
                  onClick={() => navigate(`/strategies/${strategy.id}`)}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight={600} color="text.primary">
                      {strategy.name}
                    </Typography>
                    <Typography variant="caption" color="text.tertiary">
                      {strategy.strategy_key}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      v{strategy.latest_version_no || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={translateStrategyType(strategy.strategy_type)} 
                      size="small" 
                      color={getTypeColor(strategy.strategy_type)}
                      sx={{ fontSize: 10, height: 20 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Stack direction="row" spacing={0.5}>
                      {strategy.labels.slice(0, 3).map(label => (
                        <Chip key={label} label={label} size="small" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
                      ))}
                      {strategy.labels.length > 3 && (
                        <Chip label={`+${strategy.labels.length - 3}`} size="small" variant="outlined" sx={{ fontSize: 10, height: 20 }} />
                      )}
                    </Stack>
                  </TableCell>
                  <TableCell>
                    <Box 
                      sx={{ 
                        width: 8, 
                        height: 8, 
                        borderRadius: '50%', 
                        bgcolor: strategy.is_active ? 'status.success' : 'text.disabled' 
                      }} 
                    />
                  </TableCell>
                  <TableCell align="right">
                    {strategy.last_7d_return_pct !== null ? (
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          color: strategy.last_7d_return_pct >= 0 ? 'status.success' : 'status.danger',
                          fontVariantNumeric: 'tabular-nums'
                        }}
                      >
                        {strategy.last_7d_return_pct > 0 ? '+' : ''}{strategy.last_7d_return_pct.toFixed(2)}%
                      </Typography>
                    ) : (
                      <Typography variant="body2" color="text.disabled">데이터 없음</Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {formatRelativeTime(strategy.updated_at)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      <Tooltip title="보기">
                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); navigate(`/strategies/${strategy.id}`); }}>
                          <Eye size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="편집">
                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); navigate(`/strategies/${strategy.id}/edit`); }}>
                          <Edit2 size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="백테스트 실행">
                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); }}>
                          <Play size={16} />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="세션 시작">
                        <IconButton size="small" onClick={(e) => { e.stopPropagation(); }}>
                          <Activity size={16} />
                        </IconButton>
                      </Tooltip>
                    </Stack>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}
