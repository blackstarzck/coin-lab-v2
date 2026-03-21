import { useState } from 'react'
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
  Tabs,
  Tab,
  TextField,
  Select,
  MenuItem,
  Chip,
  Skeleton,
  Tooltip,
} from '@mui/material'
import { AlertCircle } from 'lucide-react'

import { useLogs, type LogChannel } from '@/features/logs/api'
import {
  formatDateTime,
  translateLogChannel,
  translateLogLevel,
  translateMode,
} from '@/shared/lib/i18n'
import { LabPageHeader } from '@/shared/ui/LabPageHeader'

const CHANNELS: Array<{ label: string; value: LogChannel }> = [
  { label: '시스템', value: 'system' },
  { label: '전략 실행', value: 'strategy-execution' },
  { label: '주문 시뮬레이션', value: 'order-simulation' },
  { label: '리스크 제어', value: 'risk-control' },
  { label: '문서', value: 'documents' },
]

function getLevelColor(level: string) {
  switch (level.toLowerCase()) {
    case 'info':
      return 'status.info'
    case 'warning':
      return 'status.warning'
    case 'error':
    case 'critical':
      return 'status.danger'
    case 'debug':
    default:
      return 'text.secondary'
  }
}

export default function LogsPage() {
  const [tabIndex, setTabIndex] = useState(0)
  const [levelFilter, setLevelFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')

  const currentChannel = CHANNELS[tabIndex].value
  const { data: logs, isLoading } = useLogs(currentChannel)

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setTabIndex(newValue)
  }

  const filteredLogs = logs?.filter((log) => {
    if (levelFilter !== 'all' && log.level !== levelFilter) return false
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <LabPageHeader
        eyebrow="EXECUTION TRAIL"
        title="로그"
        description="시스템, 전략 실행, 주문, 리스크 이벤트를 채널별로 탐색합니다."
      />

      <Box sx={{ borderBottom: 1, borderColor: 'border.default' }}>
        <Tabs value={tabIndex} onChange={handleTabChange} variant="scrollable" scrollButtons="auto">
          {CHANNELS.map((channel) => (
            <Tab key={channel.value} label={channel.label} />
          ))}
        </Tabs>
      </Box>

      <Card>
        <CardContent sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            size="small"
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="all">전체 레벨</MenuItem>
            <MenuItem value="debug">디버그</MenuItem>
            <MenuItem value="info">정보</MenuItem>
            <MenuItem value="warning">경고</MenuItem>
            <MenuItem value="error">오류</MenuItem>
          </Select>
          <TextField
            placeholder="로그 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
            fullWidth
          />
        </CardContent>
      </Card>

      <Card>
        {isLoading ? (
          <Skeleton variant="rectangular" height={400} />
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 160 }}>시간</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 100 }}>레벨</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 90 }}>모드</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 160 }}>추적 ID</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 150 }}>소스</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>메시지</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredLogs?.map((log) => (
                <TableRow key={log.id} hover sx={{ '& td': { py: 0.5 } }}>
                  <TableCell sx={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {formatDateTime(log.timestamp)}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={translateLogLevel(log.level)}
                      size="small"
                      sx={{
                        bgcolor: getLevelColor(log.level),
                        color: 'background.paper',
                        fontWeight: 600,
                        fontSize: '0.65rem',
                        height: 20,
                      }}
                    />
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary', fontSize: '0.85rem' }}>
                    {log.mode ? translateMode(log.mode) : '-'}
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {log.trace_id ?? '-'}
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary', fontSize: '0.85rem' }}>
                    {translateLogChannel(log.channel)}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <Tooltip title={log.message} placement="top-start">
                      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                        {log.message}
                      </Typography>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
              {(!filteredLogs || filteredLogs.length === 0) && (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 8, color: 'text.secondary' }}>
                    <AlertCircle size={48} style={{ margin: '0 auto', opacity: 0.5, marginBottom: 16 }} />
                    <Typography variant="h6" color="text.secondary">
                      이 채널에는 로그가 없습니다.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        )}
      </Card>
    </Box>
  )
}
