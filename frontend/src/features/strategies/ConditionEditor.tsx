import { Add, Delete } from '@mui/icons-material'
import {
  Box,
  Button,
  Card,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material'
import type { SelectChangeEvent } from '@mui/material/Select'

import { MuiNumberField } from '@/shared/ui/MuiNumberField'

type JsonObject = Record<string, unknown>

const LOGIC_OPTIONS = ['all', 'any', 'not'] as const
const LEAF_TYPES = [
  'indicator_compare',
  'threshold_compare',
  'cross_over',
  'cross_under',
  'price_breakout',
  'volume_spike',
  'rsi_range',
  'candle_pattern',
  'regime_match',
] as const
const COMPARISON_OPERATORS = ['>', '>=', '<', '<=', '==', '!='] as const
const FIELD_PANEL_SX = {
  border: '1px solid',
  borderColor: 'divider',
  borderRadius: 2,
  bgcolor: 'bg.surface2',
  px: 2,
  py: 1.75,
} as const
const SOURCE_FIELD_GRID_SX = {
  display: 'grid',
  gap: 2,
  width: '100%',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
  alignItems: 'start',
} as const
const SOURCE_CARD_GRID_SX = {
  display: 'grid',
  gap: 2,
  width: '100%',
  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 340px), 1fr))',
  alignItems: 'start',
} as const
const LOGIC_LABELS: Record<(typeof LOGIC_OPTIONS)[number], string> = {
  all: '모든 조건',
  any: '조건 중 하나',
  not: '조건 반전',
}
const LEAF_LABELS: Record<(typeof LEAF_TYPES)[number], string> = {
  indicator_compare: '지표 비교',
  threshold_compare: '임계값 비교',
  cross_over: '상향 돌파',
  cross_under: '하향 이탈',
  price_breakout: '가격 돌파',
  volume_spike: '거래량 급증',
  rsi_range: '상대강도지수 범위',
  candle_pattern: '캔들 패턴',
  regime_match: '장세 일치',
}
const SOURCE_KIND_LABELS = {
  price: '가격 항목',
  indicator: '지표',
  derived: '파생 지표',
  constant: '고정값',
} as const
const TOKEN_LABELS: Record<string, string> = {
  highest_high: '최고가',
  lowest_low: '최저가',
  volume_ratio: '거래량 비율',
  bullish_engulfing: '상승 장악형',
  bearish_engulfing: '하락 장악형',
  inside_bar_break: '인사이드 바 돌파',
  long_lower_wick: '긴 아래꼬리',
  trend_up: '상승 추세',
  trend_down: '하락 추세',
  range: '박스권',
  high_volatility: '고변동성',
  low_volatility: '저변동성',
}

function asObject(value: unknown): JsonObject {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as JsonObject) : {}
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback
}

function updateParams(ref: JsonObject, key: string, value: unknown): JsonObject {
  const params = asObject(ref.params)
  return {
    ...ref,
    params: {
      ...params,
      [key]: value,
    },
  }
}

function formatTokenLabel(value: string): string {
  if (TOKEN_LABELS[value]) {
    return TOKEN_LABELS[value]
  }
  return value
    .split('_')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

function getLogicLabel(value: string): string {
  return LOGIC_LABELS[value as (typeof LOGIC_OPTIONS)[number]] ?? formatTokenLabel(value)
}

function getLeafLabel(value: string): string {
  return LEAF_LABELS[value as (typeof LEAF_TYPES)[number]] ?? formatTokenLabel(value)
}

function getSourceKindLabel(value: string): string {
  return SOURCE_KIND_LABELS[value as keyof typeof SOURCE_KIND_LABELS] ?? formatTokenLabel(value)
}

function createDefaultSource(kind: 'price' | 'indicator' | 'derived' | 'constant' = 'price'): JsonObject {
  if (kind === 'indicator') {
    return { kind: 'indicator', name: 'ema', params: { length: 20 } }
  }
  if (kind === 'derived') {
    return { kind: 'derived', name: 'highest_high', params: { lookback: 20, exclude_current: true } }
  }
  if (kind === 'constant') {
    return { kind: 'constant', value: 0 }
  }
  return { kind: 'price', field: 'close' }
}

function createDefaultLeaf(type: (typeof LEAF_TYPES)[number] = 'indicator_compare'): JsonObject {
  switch (type) {
    case 'threshold_compare':
      return {
        type,
        left: createDefaultSource('indicator'),
        operator: '>=',
        right: createDefaultSource('constant'),
      }
    case 'cross_over':
    case 'cross_under':
      return {
        type,
        left: createDefaultSource('price'),
        right: createDefaultSource('indicator'),
        lookback_bars: 1,
      }
    case 'price_breakout':
      return {
        type,
        source: createDefaultSource('price'),
        operator: '>',
        reference: createDefaultSource('derived'),
      }
    case 'volume_spike':
      return {
        type,
        source: { kind: 'derived', name: 'volume_ratio', params: { lookback: 20 } },
        operator: '>=',
        threshold: 2,
      }
    case 'rsi_range':
      return {
        type,
        source: { kind: 'indicator', name: 'rsi', params: { length: 14 } },
        min: 45,
        max: 65,
      }
    case 'candle_pattern':
      return {
        type,
        pattern: 'bullish_engulfing',
        timeframe: '5m',
      }
    case 'regime_match':
      return {
        type,
        regime: 'trend_up',
      }
    default:
      return {
        type,
        left: createDefaultSource('indicator'),
        operator: '>',
        right: createDefaultSource('indicator'),
      }
  }
}

function createDefaultNode(): JsonObject {
  return {
    logic: 'all',
    conditions: [createDefaultLeaf()],
  }
}

function SourceRefEditor({
  label,
  value,
  onChange,
}: {
  label: string
  value: JsonObject
  onChange: (next: JsonObject) => void
}) {
  const kind = asString(value.kind, 'price')
  const indicatorName = asString(value.name, kind === 'indicator' ? 'ema' : 'highest_high')
  const params = asObject(value.params)

  return (
    <Box sx={FIELD_PANEL_SX}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="overline" sx={{ color: 'text.secondary', letterSpacing: 0.6, lineHeight: 1.2 }}>
            {label}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
            {getSourceKindLabel(kind)}
          </Typography>
        </Box>

        <Box sx={SOURCE_FIELD_GRID_SX}>
          <Box>
            <FormControl fullWidth size="small">
              <InputLabel>데이터 유형</InputLabel>
              <Select
                value={kind}
                label="데이터 유형"
                onChange={(event: SelectChangeEvent) => onChange(createDefaultSource(event.target.value as 'price' | 'indicator' | 'derived' | 'constant'))}
              >
                <MenuItem value="price">{getSourceKindLabel('price')}</MenuItem>
                <MenuItem value="indicator">{getSourceKindLabel('indicator')}</MenuItem>
                <MenuItem value="derived">{getSourceKindLabel('derived')}</MenuItem>
                <MenuItem value="constant">{getSourceKindLabel('constant')}</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {kind === 'price' ? (
            <Box>
              <FormControl fullWidth size="small">
                <InputLabel>가격 항목</InputLabel>
                <Select
                  value={asString(value.field, 'close')}
                  label="가격 항목"
                  onChange={(event: SelectChangeEvent) => onChange({ ...value, kind: 'price', field: event.target.value })}
                >
                  <MenuItem value="open">시가</MenuItem>
                  <MenuItem value="high">고가</MenuItem>
                  <MenuItem value="low">저가</MenuItem>
                  <MenuItem value="close">종가</MenuItem>
                  <MenuItem value="volume">거래량</MenuItem>
                </Select>
              </FormControl>
            </Box>
          ) : null}

          {kind === 'indicator' ? (
            <>
              <Box>
                <FormControl fullWidth size="small">
                  <InputLabel>지표</InputLabel>
                  <Select
                    value={indicatorName}
                    label="지표"
                    onChange={(event: SelectChangeEvent) => onChange({
                      ...value,
                      kind: 'indicator',
                      name: event.target.value,
                      params: event.target.value === 'rsi' ? { length: 14 } : { length: 20 },
                    })}
                  >
                    <MenuItem value="ema">지수이동평균</MenuItem>
                    <MenuItem value="rsi">상대강도지수</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <MuiNumberField
                  label="기간"
                  size="small"
                  fullWidth
                  value={asNumber(params.length, indicatorName === 'rsi' ? 14 : 20)}
                  onValueChange={(nextValue) => onChange(
                    updateParams(
                      { ...value, kind: 'indicator', name: indicatorName },
                      'length',
                      typeof nextValue === 'number' && Number.isFinite(nextValue)
                        ? nextValue
                        : (indicatorName === 'rsi' ? 14 : 20),
                    ),
                  )}
                  step={1}
                />
              </Box>
            </>
          ) : null}

          {kind === 'derived' ? (
            <>
              <Box>
                <FormControl fullWidth size="small">
                  <InputLabel>파생 지표</InputLabel>
                  <Select
                    value={indicatorName}
                    label="파생 지표"
                    onChange={(event: SelectChangeEvent) => {
                      const nextName = event.target.value
                      onChange({
                        kind: 'derived',
                        name: nextName,
                        params: nextName === 'volume_ratio'
                          ? { lookback: 20 }
                          : { lookback: 20, exclude_current: true },
                      })
                    }}
                  >
                    <MenuItem value="highest_high">{formatTokenLabel('highest_high')}</MenuItem>
                    <MenuItem value="lowest_low">{formatTokenLabel('lowest_low')}</MenuItem>
                    <MenuItem value="volume_ratio">{formatTokenLabel('volume_ratio')}</MenuItem>
                  </Select>
                </FormControl>
              </Box>
              <Box>
                <MuiNumberField
                  label="조회 봉 수"
                  size="small"
                  fullWidth
                  value={asNumber(params.lookback, 20)}
                  onValueChange={(nextValue) => onChange(
                    updateParams(
                      { ...value, kind: 'derived', name: indicatorName },
                      'lookback',
                      typeof nextValue === 'number' && Number.isFinite(nextValue) ? nextValue : 20,
                    ),
                  )}
                  step={1}
                />
              </Box>
              {indicatorName !== 'volume_ratio' ? (
                <Box sx={{ gridColumn: '1 / -1' }}>
                  <Box
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 1,
                      px: 1,
                      py: 0.5,
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: 'divider',
                    }}
                  >
                    <Switch
                      size="small"
                      checked={Boolean(params.exclude_current)}
                      onChange={(event) => onChange(updateParams({ ...value, kind: 'derived', name: indicatorName }, 'exclude_current', event.target.checked))}
                    />
                    <Typography variant="body2">현재 캔들 제외</Typography>
                  </Box>
                </Box>
              ) : null}
            </>
          ) : null}

          {kind === 'constant' ? (
            <Box>
              <MuiNumberField
                label="값"
                size="small"
                fullWidth
                value={asNumber(value.value, 0)}
                onValueChange={(nextValue) => onChange({
                  kind: 'constant',
                  value: typeof nextValue === 'number' && Number.isFinite(nextValue) ? nextValue : 0,
                })}
                step={0.1}
              />
            </Box>
          ) : null}
        </Box>
      </Stack>
    </Box>
  )
}

function LeafEditor({
  value,
  onChange,
}: {
  value: JsonObject
  onChange: (next: JsonObject) => void
}) {
  const type = asString(value.type, 'indicator_compare') as (typeof LEAF_TYPES)[number]

  return (
    <Stack spacing={2.5}>
      <Box sx={{ maxWidth: 320 }}>
        <FormControl fullWidth size="small">
          <InputLabel>조건 유형</InputLabel>
          <Select
            value={type}
            label="조건 유형"
            onChange={(event: SelectChangeEvent) => onChange(createDefaultLeaf(event.target.value as (typeof LEAF_TYPES)[number]))}
          >
            {LEAF_TYPES.map((item) => (
              <MenuItem key={item} value={item}>
                {getLeafLabel(item)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {(type === 'indicator_compare' || type === 'threshold_compare') ? (
        <Stack spacing={2}>
          <Box sx={{ maxWidth: 220 }}>
            <FormControl fullWidth size="small">
              <InputLabel>연산자</InputLabel>
              <Select
                value={asString(value.operator, '>')}
                label="연산자"
                onChange={(event: SelectChangeEvent) => onChange({ ...value, operator: event.target.value })}
              >
                {COMPARISON_OPERATORS.map((operator) => (
                  <MenuItem key={operator} value={operator}>{operator}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Box sx={SOURCE_CARD_GRID_SX}>
            <Box>
              <SourceRefEditor label="좌변 값" value={asObject(value.left)} onChange={(next) => onChange({ ...value, left: next })} />
            </Box>
            <Box>
              <SourceRefEditor label="우변 값" value={asObject(value.right)} onChange={(next) => onChange({ ...value, right: next })} />
            </Box>
          </Box>
        </Stack>
      ) : null}

      {(type === 'cross_over' || type === 'cross_under') ? (
        <Stack spacing={2}>
          <Box sx={{ maxWidth: 220 }}>
            <MuiNumberField
              label="조회 봉 수"
              size="small"
              fullWidth
              value={asNumber(value.lookback_bars, 1)}
              onValueChange={(nextValue) => onChange({
                ...value,
                lookback_bars: typeof nextValue === 'number' && Number.isFinite(nextValue) ? nextValue : 1,
              })}
              step={1}
            />
          </Box>
          <Box sx={SOURCE_CARD_GRID_SX}>
            <Box>
              <SourceRefEditor label="좌변 값" value={asObject(value.left)} onChange={(next) => onChange({ ...value, left: next })} />
            </Box>
            <Box>
              <SourceRefEditor label="우변 값" value={asObject(value.right)} onChange={(next) => onChange({ ...value, right: next })} />
            </Box>
          </Box>
        </Stack>
      ) : null}

      {type === 'price_breakout' ? (
        <Stack spacing={2}>
          <Box sx={{ maxWidth: 220 }}>
            <FormControl fullWidth size="small">
              <InputLabel>연산자</InputLabel>
              <Select
                value={asString(value.operator, '>')}
                label="연산자"
                onChange={(event: SelectChangeEvent) => onChange({ ...value, operator: event.target.value })}
              >
                {COMPARISON_OPERATORS.map((operator) => (
                  <MenuItem key={operator} value={operator}>{operator}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Box sx={SOURCE_CARD_GRID_SX}>
            <Box>
              <SourceRefEditor label="기준 값" value={asObject(value.source)} onChange={(next) => onChange({ ...value, source: next })} />
            </Box>
            <Box>
              <SourceRefEditor label="참조 값" value={asObject(value.reference)} onChange={(next) => onChange({ ...value, reference: next })} />
            </Box>
          </Box>
        </Stack>
      ) : null}

      {type === 'volume_spike' ? (
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>연산자</InputLabel>
                <Select
                  value={asString(value.operator, '>=')}
                  label="연산자"
                  onChange={(event: SelectChangeEvent) => onChange({ ...value, operator: event.target.value })}
                >
                  {COMPARISON_OPERATORS.map((operator) => (
                    <MenuItem key={operator} value={operator}>{operator}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <MuiNumberField
                label="기준값"
                size="small"
                fullWidth
                value={asNumber(value.threshold, 2)}
                onValueChange={(nextValue) => onChange({
                  ...value,
                  threshold: typeof nextValue === 'number' && Number.isFinite(nextValue) ? nextValue : 2,
                })}
                step={0.1}
              />
            </Grid>
          </Grid>
          <SourceRefEditor label="기준 값" value={asObject(value.source)} onChange={(next) => onChange({ ...value, source: next })} />
        </Stack>
      ) : null}

      {type === 'rsi_range' ? (
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <MuiNumberField
                label="최소값"
                size="small"
                fullWidth
                value={asNumber(value.min, 45)}
                onValueChange={(nextValue) => onChange({
                  ...value,
                  min: typeof nextValue === 'number' && Number.isFinite(nextValue) ? nextValue : 45,
                })}
                step={0.1}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <MuiNumberField
                label="최대값"
                size="small"
                fullWidth
                value={asNumber(value.max, 65)}
                onValueChange={(nextValue) => onChange({
                  ...value,
                  max: typeof nextValue === 'number' && Number.isFinite(nextValue) ? nextValue : 65,
                })}
                step={0.1}
              />
            </Grid>
          </Grid>
          <SourceRefEditor label="기준 값" value={asObject(value.source)} onChange={(next) => onChange({ ...value, source: next })} />
        </Stack>
      ) : null}

      {type === 'candle_pattern' ? (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>패턴</InputLabel>
              <Select
                value={asString(value.pattern, 'bullish_engulfing')}
                label="패턴"
                onChange={(event: SelectChangeEvent) => onChange({ ...value, pattern: event.target.value })}
              >
                {['bullish_engulfing', 'bearish_engulfing', 'inside_bar_break', 'long_lower_wick'].map((pattern) => (
                  <MenuItem key={pattern} value={pattern}>{formatTokenLabel(pattern)}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={4}>
            <TextField
              label="시간 주기"
              size="small"
              fullWidth
              value={asString(value.timeframe, '5m')}
              onChange={(event) => onChange({ ...value, timeframe: event.target.value })}
            />
          </Grid>
        </Grid>
      ) : null}

      {type === 'regime_match' ? (
        <Box sx={{ maxWidth: 320 }}>
          <FormControl fullWidth size="small">
            <InputLabel>장세</InputLabel>
            <Select
              value={asString(value.regime, 'trend_up')}
              label="장세"
              onChange={(event: SelectChangeEvent) => onChange({ ...value, regime: event.target.value })}
            >
              {['trend_up', 'trend_down', 'range', 'high_volatility', 'low_volatility'].map((regime) => (
                <MenuItem key={regime} value={regime}>{formatTokenLabel(regime)}</MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      ) : null}
    </Stack>
  )
}

interface ConditionEditorProps {
  label: string
  value: JsonObject
  onChange: (next: JsonObject) => void
  onRemove?: () => void
  depth?: number
}

export function ConditionEditor({
  label,
  value,
  onChange,
  onRemove,
  depth = 0,
}: ConditionEditorProps) {
  const isLogicBlock = typeof value.logic === 'string'
  const logicValue = asString(value.logic, 'all')
  const isNotBlock = logicValue === 'not'
  const conditions = asArray(value.conditions)
  const leafType = asString(value.type, 'indicator_compare')

  return (
    <Card
      variant="outlined"
      sx={{
        width: '100%',
        borderRadius: depth === 0 ? 3 : 2.5,
        borderColor: depth === 0 ? 'divider' : 'rgba(255,255,255,0.08)',
        bgcolor: depth === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
        boxShadow: 'none',
      }}
    >
      <Box sx={{ p: depth === 0 ? 2.5 : 2.25 }}>
        <Stack spacing={2.5}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            justifyContent="space-between"
            alignItems={{ xs: 'flex-start', sm: 'center' }}
            spacing={1.5}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle2" fontWeight={700}>
                {label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {isLogicBlock
                  ? `${getLogicLabel(logicValue)} · ${isNotBlock ? '하위 조건 1개' : `하위 조건 ${conditions.length}개`}`
                  : getLeafLabel(leafType)}
              </Typography>
            </Box>

            {onRemove ? (
              <IconButton
                size="small"
                onClick={onRemove}
                sx={{ alignSelf: { xs: 'flex-end', sm: 'center' } }}
              >
                <Delete fontSize="small" />
              </IconButton>
            ) : null}
          </Stack>

          <Box sx={{ maxWidth: 320 }}>
            <FormControl fullWidth size="small">
              <InputLabel>노드 유형</InputLabel>
              <Select
                value={isLogicBlock ? logicValue : 'leaf'}
                label="노드 유형"
                onChange={(event: SelectChangeEvent) => {
                  const nextValue = event.target.value
                  if (nextValue === 'leaf') {
                    onChange(createDefaultLeaf())
                    return
                  }
                  if (nextValue === 'not') {
                    onChange({ logic: 'not', condition: createDefaultLeaf() })
                    return
                  }
                  onChange({ logic: nextValue, conditions: [createDefaultLeaf()] })
                }}
              >
                {LOGIC_OPTIONS.map((logic) => (
                  <MenuItem key={logic} value={logic}>{getLogicLabel(logic)}</MenuItem>
                ))}
                <MenuItem value="leaf">단일 조건</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {isLogicBlock ? (
            isNotBlock ? (
              <ConditionEditor
                label="반전 조건"
                value={asObject(value.condition)}
                onChange={(next) => onChange({ logic: 'not', condition: next })}
                depth={depth + 1}
              />
            ) : (
              <Stack spacing={2}>
                {conditions.map((condition, index) => (
                  <ConditionEditor
                    key={`${label}-${index}`}
                    label={`조건 ${index + 1}`}
                    value={asObject(condition)}
                    onChange={(next) => {
                      const nextConditions = [...conditions]
                      nextConditions[index] = next
                      onChange({ ...value, conditions: nextConditions })
                    }}
                    onRemove={() => {
                      const nextConditions = conditions.filter((_, conditionIndex) => conditionIndex !== index)
                      onChange({
                        ...value,
                        conditions: nextConditions.length > 0 ? nextConditions : [createDefaultLeaf()],
                      })
                    }}
                    depth={depth + 1}
                  />
                ))}

                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={() => onChange({ ...value, conditions: [...conditions, createDefaultLeaf()] })}
                  sx={{
                    alignSelf: 'flex-start',
                    borderStyle: 'dashed',
                    px: 2,
                  }}
                >
                  하위 조건 추가
                </Button>
              </Stack>
            )
          ) : (
            <LeafEditor value={value} onChange={onChange} />
          )}
        </Stack>
      </Box>
    </Card>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function defaultConditionNode(): JsonObject {
  return createDefaultNode()
}
