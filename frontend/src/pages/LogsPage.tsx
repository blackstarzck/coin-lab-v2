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
import { format } from 'date-fns'

import { useLogs } from '@/features/logs/api'

import { AlertCircle } from 'lucide-react'

const CHANNELS = [
  { label: 'System', value: 'system' },
  { label: 'Strategy Execution', value: 'strategy-execution' },
  { label: 'Order Simulation', value: 'order-simulation' },
  { label: 'Risk Control', value: 'risk-control' },
  { label: 'Documents', value: 'documents' },
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

  const filteredLogs = logs?.filter(log => {
    if (levelFilter !== 'all' && log.level !== levelFilter) return false
    if (searchQuery && !log.message.toLowerCase().includes(searchQuery.toLowerCase())) return false
    return true
  })

  return (
    <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h4" sx={{ fontWeight: 600 }}>
        System Logs
      </Typography>

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
            <MenuItem value="all">All Levels</MenuItem>
            <MenuItem value="debug">Debug</MenuItem>
            <MenuItem value="info">Info</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="error">Error</MenuItem>
          </Select>
          <TextField
            placeholder="Search logs..."
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
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 160 }}>Time</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 100 }}>Level</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 90 }}>Mode</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 160 }}>Trace</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12, width: 150 }}>Source</TableCell>
                <TableCell sx={{ color: 'text.tertiary', fontSize: 12 }}>Message</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredLogs?.map((log) => (
                <TableRow key={log.id} hover sx={{ '& td': { py: 0.5 } }}>
                  <TableCell sx={{ fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {format(new Date(log.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={log.level.toUpperCase()}
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
                    {log.mode ?? '-'}
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {log.trace_id ?? '-'}
                  </TableCell>
                  <TableCell sx={{ color: 'text.secondary', fontSize: '0.85rem' }}>
                    {log.channel}
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
                      No log entries for this channel.
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
