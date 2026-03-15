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
const LOGIC_LABELS: Record<(typeof LOGIC_OPTIONS)[number], string> = {
  all: 'All conditions',
  any: 'Any condition',
  not: 'Invert condition',
}
const LEAF_LABELS: Record<(typeof LEAF_TYPES)[number], string> = {
  indicator_compare: 'Indicator compare',
  threshold_compare: 'Threshold compare',
  cross_over: 'Cross over',
  cross_under: 'Cross under',
  price_breakout: 'Price breakout',
  volume_spike: 'Volume spike',
  rsi_range: 'RSI range',
  candle_pattern: 'Candle pattern',
  regime_match: 'Regime match',
}
const SOURCE_KIND_LABELS = {
  price: 'Price field',
  indicator: 'Indicator',
  derived: 'Derived metric',
  constant: 'Constant',
} as const

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

        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Source Type</InputLabel>
              <Select
                value={kind}
                label="Source Type"
                onChange={(event: SelectChangeEvent) => onChange(createDefaultSource(event.target.value as 'price' | 'indicator' | 'derived' | 'constant'))}
              >
                <MenuItem value="price">{getSourceKindLabel('price')}</MenuItem>
                <MenuItem value="indicator">{getSourceKindLabel('indicator')}</MenuItem>
                <MenuItem value="derived">{getSourceKindLabel('derived')}</MenuItem>
                <MenuItem value="constant">{getSourceKindLabel('constant')}</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          {kind === 'price' ? (
            <Grid item xs={12} md={8}>
              <FormControl fullWidth size="small">
                <InputLabel>Field</InputLabel>
                <Select
                  value={asString(value.field, 'close')}
                  label="Field"
                  onChange={(event: SelectChangeEvent) => onChange({ ...value, kind: 'price', field: event.target.value })}
                >
                  <MenuItem value="open">Open</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="close">Close</MenuItem>
                  <MenuItem value="volume">Volume</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          ) : null}

          {kind === 'indicator' ? (
            <>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth size="small">
                  <InputLabel>Indicator</InputLabel>
                  <Select
                    value={indicatorName}
                    label="Indicator"
                    onChange={(event: SelectChangeEvent) => onChange({
                      ...value,
                      kind: 'indicator',
                      name: event.target.value,
                      params: event.target.value === 'rsi' ? { length: 14 } : { length: 20 },
                    })}
                  >
                    <MenuItem value="ema">EMA</MenuItem>
                    <MenuItem value="rsi">RSI</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  label="Length"
                  type="number"
                  size="small"
                  fullWidth
                  value={asNumber(params.length, indicatorName === 'rsi' ? 14 : 20)}
                  onChange={(event) => onChange(updateParams({ ...value, kind: 'indicator', name: indicatorName }, 'length', Number(event.target.value)))}
                />
              </Grid>
            </>
          ) : null}

          {kind === 'derived' ? (
            <>
              <Grid item xs={12} md={4}>
                <FormControl fullWidth size="small">
                  <InputLabel>Derived Metric</InputLabel>
                  <Select
                    value={indicatorName}
                    label="Derived Metric"
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
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  label="Lookback"
                  type="number"
                  size="small"
                  fullWidth
                  value={asNumber(params.lookback, 20)}
                  onChange={(event) => onChange(updateParams({ ...value, kind: 'derived', name: indicatorName }, 'lookback', Number(event.target.value)))}
                />
              </Grid>
              {indicatorName !== 'volume_ratio' ? (
                <Grid item xs={12}>
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
                    <Typography variant="body2">Exclude current candle</Typography>
                  </Box>
                </Grid>
              ) : null}
            </>
          ) : null}

          {kind === 'constant' ? (
            <Grid item xs={12} md={4}>
              <TextField
                label="Value"
                type="number"
                size="small"
                fullWidth
                value={asNumber(value.value, 0)}
                onChange={(event) => onChange({ kind: 'constant', value: Number(event.target.value) })}
              />
            </Grid>
          ) : null}
        </Grid>
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
          <InputLabel>Condition Type</InputLabel>
          <Select
            value={type}
            label="Condition Type"
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
              <InputLabel>Operator</InputLabel>
              <Select
                value={asString(value.operator, '>')}
                label="Operator"
                onChange={(event: SelectChangeEvent) => onChange({ ...value, operator: event.target.value })}
              >
                {COMPARISON_OPERATORS.map((operator) => (
                  <MenuItem key={operator} value={operator}>{operator}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} xl={6}>
              <SourceRefEditor label="Left source" value={asObject(value.left)} onChange={(next) => onChange({ ...value, left: next })} />
            </Grid>
            <Grid item xs={12} xl={6}>
              <SourceRefEditor label="Right source" value={asObject(value.right)} onChange={(next) => onChange({ ...value, right: next })} />
            </Grid>
          </Grid>
        </Stack>
      ) : null}

      {(type === 'cross_over' || type === 'cross_under') ? (
        <Stack spacing={2}>
          <Box sx={{ maxWidth: 220 }}>
            <TextField
              label="Lookback Bars"
              type="number"
              size="small"
              fullWidth
              value={asNumber(value.lookback_bars, 1)}
              onChange={(event) => onChange({ ...value, lookback_bars: Number(event.target.value) })}
            />
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} xl={6}>
              <SourceRefEditor label="Left source" value={asObject(value.left)} onChange={(next) => onChange({ ...value, left: next })} />
            </Grid>
            <Grid item xs={12} xl={6}>
              <SourceRefEditor label="Right source" value={asObject(value.right)} onChange={(next) => onChange({ ...value, right: next })} />
            </Grid>
          </Grid>
        </Stack>
      ) : null}

      {type === 'price_breakout' ? (
        <Stack spacing={2}>
          <Box sx={{ maxWidth: 220 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Operator</InputLabel>
              <Select
                value={asString(value.operator, '>')}
                label="Operator"
                onChange={(event: SelectChangeEvent) => onChange({ ...value, operator: event.target.value })}
              >
                {COMPARISON_OPERATORS.map((operator) => (
                  <MenuItem key={operator} value={operator}>{operator}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
          <Grid container spacing={2}>
            <Grid item xs={12} xl={6}>
              <SourceRefEditor label="Source" value={asObject(value.source)} onChange={(next) => onChange({ ...value, source: next })} />
            </Grid>
            <Grid item xs={12} xl={6}>
              <SourceRefEditor label="Reference" value={asObject(value.reference)} onChange={(next) => onChange({ ...value, reference: next })} />
            </Grid>
          </Grid>
        </Stack>
      ) : null}

      {type === 'volume_spike' ? (
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Operator</InputLabel>
                <Select
                  value={asString(value.operator, '>=')}
                  label="Operator"
                  onChange={(event: SelectChangeEvent) => onChange({ ...value, operator: event.target.value })}
                >
                  {COMPARISON_OPERATORS.map((operator) => (
                    <MenuItem key={operator} value={operator}>{operator}</MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Threshold"
                type="number"
                size="small"
                fullWidth
                value={asNumber(value.threshold, 2)}
                onChange={(event) => onChange({ ...value, threshold: Number(event.target.value) })}
              />
            </Grid>
          </Grid>
          <SourceRefEditor label="Source" value={asObject(value.source)} onChange={(next) => onChange({ ...value, source: next })} />
        </Stack>
      ) : null}

      {type === 'rsi_range' ? (
        <Stack spacing={2}>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <TextField
                label="Min"
                type="number"
                size="small"
                fullWidth
                value={asNumber(value.min, 45)}
                onChange={(event) => onChange({ ...value, min: Number(event.target.value) })}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Max"
                type="number"
                size="small"
                fullWidth
                value={asNumber(value.max, 65)}
                onChange={(event) => onChange({ ...value, max: Number(event.target.value) })}
              />
            </Grid>
          </Grid>
          <SourceRefEditor label="Source" value={asObject(value.source)} onChange={(next) => onChange({ ...value, source: next })} />
        </Stack>
      ) : null}

      {type === 'candle_pattern' ? (
        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <FormControl fullWidth size="small">
              <InputLabel>Pattern</InputLabel>
              <Select
                value={asString(value.pattern, 'bullish_engulfing')}
                label="Pattern"
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
              label="Timeframe"
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
            <InputLabel>Regime</InputLabel>
            <Select
              value={asString(value.regime, 'trend_up')}
              label="Regime"
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
                  ? `${getLogicLabel(logicValue)} · ${isNotBlock ? 'single nested condition' : `${conditions.length} nested condition${conditions.length === 1 ? '' : 's'}`}`
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
              <InputLabel>Node Type</InputLabel>
              <Select
                value={isLogicBlock ? logicValue : 'leaf'}
                label="Node Type"
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
                <MenuItem value="leaf">Single condition</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {isLogicBlock ? (
            isNotBlock ? (
              <ConditionEditor
                label="Negated condition"
                value={asObject(value.condition)}
                onChange={(next) => onChange({ logic: 'not', condition: next })}
                depth={depth + 1}
              />
            ) : (
              <Stack spacing={2}>
                {conditions.map((condition, index) => (
                  <ConditionEditor
                    key={`${label}-${index}`}
                    label={`Condition ${index + 1}`}
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
                  Add nested condition
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

export function defaultConditionNode(): JsonObject {
  return createDefaultNode()
}
