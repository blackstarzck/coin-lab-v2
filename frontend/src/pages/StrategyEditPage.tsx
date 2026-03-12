import { useEffect, useMemo, useState } from 'react'
import type { ChangeEvent, ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  CircularProgress,
  FormControl,
  FormControlLabel,
  Grid,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material'
import { ArrowLeft, Save, X } from 'lucide-react'

import {
  useCreateStrategyVersion,
  useStrategy,
  useStrategyVersions,
  useUpdateStrategy,
  useValidateDraft,
  useValidateVersion,
} from '@/features/strategies/api'
import type { Strategy, StrategyVersion, ValidationResult } from '@/entities/strategy/types'

type JsonObject = Record<string, unknown>

interface DiffRow {
  path: string
  before: unknown
  after: unknown
}

function asObject(value: unknown): JsonObject {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as JsonObject) : {}
}

function asArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map((item) => String(item)) : []
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback
}

function parseNumberInput(value: string, fallback = 0): number {
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function parseIntegerInput(value: string, fallback = 0): number {
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) ? parsed : fallback
}

function updateNestedConfig(config: JsonObject, path: string[], value: unknown): JsonObject {
  const nextConfig: JsonObject = { ...config }
  let current: JsonObject = nextConfig
  for (let index = 0; index < path.length - 1; index += 1) {
    const key = path[index]
    current[key] = { ...asObject(current[key]) }
    current = current[key] as JsonObject
  }
  current[path[path.length - 1]] = value
  return nextConfig
}

function buildDiffRows(before: unknown, after: unknown, path = ''): DiffRow[] {
  if (JSON.stringify(before) === JSON.stringify(after)) {
    return []
  }
  const beforeIsObject = before && typeof before === 'object' && !Array.isArray(before)
  const afterIsObject = after && typeof after === 'object' && !Array.isArray(after)
  if (beforeIsObject && afterIsObject) {
    const beforeObject = before as JsonObject
    const afterObject = after as JsonObject
    const keys = Array.from(new Set([...Object.keys(beforeObject), ...Object.keys(afterObject)])).sort()
    return keys.flatMap((key) => buildDiffRows(beforeObject[key], afterObject[key], path ? `${path}.${key}` : key))
  }
  return [{ path: path || 'root', before, after }]
}

function buildDraftConfig(baseConfig: JsonObject, name: string, description: string, labels: string[], notes: string): JsonObject {
  return {
    ...baseConfig,
    name,
    description,
    labels,
    notes,
  }
}

function JsonSection({
  label,
  value,
  onChange,
}: {
  label: string
  value: JsonObject
  onChange: (next: JsonObject) => void
}) {
  return (
    <TextField
      label={label}
      multiline
      fullWidth
      rows={14}
      value={JSON.stringify(value, null, 2)}
      onChange={(event) => {
        try {
          onChange(JSON.parse(event.target.value) as JsonObject)
        } catch {
          // Allow temporary invalid typing state.
        }
      }}
      sx={{ '& textarea': { fontFamily: 'monospace' } }}
    />
  )
}

function TabPanel({ children, value, index }: { children?: ReactNode, value: number, index: number }) {
  return (
    <div hidden={value !== index} style={{ height: '100%' }}>
      {value === index ? <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>{children}</Box> : null}
    </div>
  )
}

function StrategyEditForm({
  strategy,
  versions,
  onBack,
  onSaved,
}: {
  strategy: Strategy
  versions: StrategyVersion[]
  onBack: () => void
  onSaved: () => void
}) {
  const latestVersion = versions[0]
  const updateStrategyMutation = useUpdateStrategy()
  const createVersionMutation = useCreateStrategyVersion()
  const validateDraftMutation = useValidateDraft()
  const validateVersionMutation = useValidateVersion()

  const [tabValue, setTabValue] = useState(0)
  const [name, setName] = useState(strategy.name)
  const [description, setDescription] = useState(strategy.description ?? '')
  const [labelsText, setLabelsText] = useState(strategy.labels.join(', '))
  const [notes, setNotes] = useState(latestVersion?.notes ?? '')
  const [configJson, setConfigJson] = useState<JsonObject>(latestVersion?.config_json ?? {})
  const [jsonText, setJsonText] = useState(JSON.stringify(latestVersion?.config_json ?? {}, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const labels = useMemo(() => labelsText.split(',').map((item) => item.trim()).filter(Boolean), [labelsText])
  const diffRows = useMemo(() => buildDiffRows(latestVersion?.config_json ?? {}, configJson), [latestVersion, configJson])

  const market = asObject(configJson.market)
  const universe = asObject(configJson.universe)
  const position = asObject(configJson.position)
  const risk = asObject(configJson.risk)
  const execution = asObject(configJson.execution)
  const backtest = asObject(configJson.backtest)

  const updateConfigAtPath = (path: string[], value: unknown) => {
    setConfigJson((prev) => updateNestedConfig(prev, path, value))
  }

  const updateIntegerAtPath = (path: string[], fallback = 0) => (event: ChangeEvent<HTMLInputElement>) => {
    updateConfigAtPath(path, parseIntegerInput(event.target.value, fallback))
  }

  const updateNumberAtPath = (path: string[], fallback = 0) => (event: ChangeEvent<HTMLInputElement>) => {
    updateConfigAtPath(path, parseNumberInput(event.target.value, fallback))
  }

  useEffect(() => {
    setJsonText(JSON.stringify(configJson, null, 2))
  }, [configJson])

  const handleValidate = async () => {
    const result = await validateDraftMutation.mutateAsync({
      configJson: buildDraftConfig(configJson, name, description, labels, notes),
      strict: true,
    })
    setValidationResult(result)
    setTabValue(11)
  }

  const handleSave = async () => {
    if (jsonError) return
    setSaveError(null)
    try {
      if (
        strategy.name !== name
        || (strategy.description ?? '') !== description
        || JSON.stringify(strategy.labels) !== JSON.stringify(labels)
      ) {
        await updateStrategyMutation.mutateAsync({ id: strategy.id, name, description, labels })
      }
      const createdVersion = await createVersionMutation.mutateAsync({
        strategyId: strategy.id,
        data: {
          schema_version: String(configJson.schema_version ?? latestVersion?.schema_version ?? '1.0.0'),
          config_json: buildDraftConfig(configJson, name, description, labels, notes),
          labels,
          notes,
        },
      })
      if (validationResult?.valid) {
        await validateVersionMutation.mutateAsync({ versionId: createdVersion.id, strict: true })
      }
      onSaved()
    } catch {
      setSaveError('Failed to save the new strategy version.')
    }
  }

  return (
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2, flexShrink: 0 }}>
        <IconButton onClick={onBack} sx={{ color: 'text.secondary' }}>
          <ArrowLeft size={20} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5">Edit Strategy: {strategy.name}</Typography>
          <Typography variant="body2" color="text.tertiary">
            Saving creates a new version from v{latestVersion?.version_no || 1}.
          </Typography>
        </Box>
        <Button variant="outlined" onClick={handleValidate} disabled={!!jsonError || validateDraftMutation.isPending}>
          {validateDraftMutation.isPending ? 'Validating...' : 'Validate Draft'}
        </Button>
      </Box>

      {saveError ? <Alert severity="error" sx={{ mb: 2 }}>{saveError}</Alert> : null}

      <Card sx={{ flexGrow: 1, display: 'flex', flexDirection: 'row', overflow: 'hidden' }}>
        <Tabs
          orientation="vertical"
          value={tabValue}
          onChange={(_, next) => setTabValue(next)}
          variant="scrollable"
          sx={{ minWidth: 220, borderRight: 1, borderColor: 'divider', bgcolor: 'bg.surface2' }}
        >
          <Tab label="Basic" />
          <Tab label="Market & Universe" />
          <Tab label="Entry" />
          <Tab label="Reentry" />
          <Tab label="Position" />
          <Tab label="Exit" />
          <Tab label="Risk" />
          <Tab label="Execution" />
          <Tab label="Backtest" />
          <Tab label={`Diff Preview (${diffRows.length})`} />
          <Tab label="JSON Editor" />
          <Tab label={validationResult?.valid ? 'Validation ✓' : 'Validation'} />
        </Tabs>

        <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
          <TabPanel value={tabValue} index={0}>
            <Stack spacing={3} maxWidth={760}>
              <TextField label="Strategy Name" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
              <TextField label="Description" value={description} onChange={(event) => setDescription(event.target.value)} multiline rows={3} fullWidth />
              <TextField label="Labels (comma separated)" value={labelsText} onChange={(event) => setLabelsText(event.target.value)} fullWidth />
              <TextField label="Version Notes" value={notes} onChange={(event) => setNotes(event.target.value)} multiline rows={3} fullWidth />
              <TextField label="Strategy Type" value={strategy.strategy_type.toUpperCase()} disabled fullWidth />
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Grid container spacing={3} maxWidth={840}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Exchange</InputLabel>
                  <Select value={String(market.exchange ?? 'UPBIT')} label="Exchange" onChange={(event) => updateConfigAtPath(['market', 'exchange'], event.target.value)}>
                    <MenuItem value="UPBIT">Upbit</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Trade Basis</InputLabel>
                  <Select value={String(market.trade_basis ?? 'candle')} label="Trade Basis" onChange={(event) => updateConfigAtPath(['market', 'trade_basis'], event.target.value)}>
                    <MenuItem value="candle">Candle</MenuItem>
                    <MenuItem value="tick">Tick</MenuItem>
                    <MenuItem value="hybrid">Hybrid</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Timeframes"
                  value={asArray(market.timeframes).join(', ')}
                  onChange={(event) => updateConfigAtPath(
                    ['market', 'timeframes'],
                    event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                  )}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Universe Mode</InputLabel>
                  <Select value={String(universe.mode ?? 'dynamic')} label="Universe Mode" onChange={(event) => updateConfigAtPath(['universe', 'mode'], event.target.value)}>
                    <MenuItem value="dynamic">Dynamic</MenuItem>
                    <MenuItem value="static">Static</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Max Symbols"
                  type="number"
                  value={asNumber(universe.max_symbols, 10)}
                  onChange={updateIntegerAtPath(['universe', 'max_symbols'], 10)}
                  fullWidth
                />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <JsonSection label="Entry JSON" value={asObject(configJson.entry)} onChange={(next) => setConfigJson((prev) => updateNestedConfig(prev, ['entry'], next))} />
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <JsonSection label="Reentry JSON" value={asObject(configJson.reentry)} onChange={(next) => setConfigJson((prev) => updateNestedConfig(prev, ['reentry'], next))} />
          </TabPanel>

          <TabPanel value={tabValue} index={4}>
            <Grid container spacing={3} maxWidth={840}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Max Open Positions Per Symbol"
                  type="number"
                  value={asNumber(position.max_open_positions_per_symbol, 1)}
                  onChange={updateIntegerAtPath(['position', 'max_open_positions_per_symbol'], 1)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Max Concurrent Positions"
                  type="number"
                  value={asNumber(position.max_concurrent_positions, 4)}
                  onChange={updateIntegerAtPath(['position', 'max_concurrent_positions'], 4)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel control={<Switch checked={Boolean(position.allow_scale_in)} onChange={(event) => updateConfigAtPath(['position', 'allow_scale_in'], event.target.checked)} />} label="Allow scale in" />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={5}>
            <JsonSection label="Exit JSON" value={asObject(configJson.exit)} onChange={(next) => setConfigJson((prev) => updateNestedConfig(prev, ['exit'], next))} />
          </TabPanel>

          <TabPanel value={tabValue} index={6}>
            <Grid container spacing={3} maxWidth={840}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Daily Loss Limit %"
                  type="number"
                  value={asNumber(risk.daily_loss_limit_pct, 0)}
                  onChange={updateNumberAtPath(['risk', 'daily_loss_limit_pct'])}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Max Strategy Drawdown %"
                  type="number"
                  value={asNumber(risk.max_strategy_drawdown_pct, 0)}
                  onChange={updateNumberAtPath(['risk', 'max_strategy_drawdown_pct'])}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel control={<Switch checked={Boolean(risk.kill_switch_enabled)} onChange={(event) => updateConfigAtPath(['risk', 'kill_switch_enabled'], event.target.checked)} />} label="Enable kill switch" />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={7}>
            <Grid container spacing={3} maxWidth={840}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Entry Order Type</InputLabel>
                  <Select value={String(execution.entry_order_type ?? 'market')} label="Entry Order Type" onChange={(event) => updateConfigAtPath(['execution', 'entry_order_type'], event.target.value)}>
                    <MenuItem value="market">Market</MenuItem>
                    <MenuItem value="limit">Limit</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Fee Model</InputLabel>
                  <Select value={String(execution.fee_model ?? 'per_fill')} label="Fee Model" onChange={(event) => updateConfigAtPath(['execution', 'fee_model'], event.target.value)}>
                    <MenuItem value="per_fill">Per Fill</MenuItem>
                    <MenuItem value="per_order">Per Order</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={8}>
            <Grid container spacing={3} maxWidth={840}>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Initial Capital"
                  type="number"
                  value={asNumber(backtest.initial_capital, 10000000)}
                  onChange={updateNumberAtPath(['backtest', 'initial_capital'], 10000000)}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  label="Fee (BPS)"
                  type="number"
                  value={asNumber(backtest.fee_bps, 5)}
                  onChange={updateNumberAtPath(['backtest', 'fee_bps'], 5)}
                  fullWidth
                />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={9}>
            <Stack spacing={2}>
              <Typography variant="h6">Diff Preview</Typography>
              <Typography variant="body2" color="text.secondary">{diffRows.length === 0 ? 'No changes detected.' : `${diffRows.length} changed fields`}</Typography>
              {diffRows.map((row) => (
                <Card key={row.path} variant="outlined">
                  <Box sx={{ p: 2 }}>
                    <Typography variant="subtitle2" fontFamily="monospace">{row.path}</Typography>
                    <Grid container spacing={2} sx={{ mt: 0.5 }}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="caption" color="text.secondary">Before</Typography>
                        <Box sx={{ mt: 0.5, p: 1.5, borderRadius: 1, bgcolor: 'bg.surface2', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{JSON.stringify(row.before, null, 2)}</Box>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="caption" color="text.secondary">After</Typography>
                        <Box sx={{ mt: 0.5, p: 1.5, borderRadius: 1, bgcolor: 'rgba(34, 231, 107, 0.05)', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{JSON.stringify(row.after, null, 2)}</Box>
                      </Grid>
                    </Grid>
                  </Box>
                </Card>
              ))}
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={10}>
            {jsonError ? <Alert severity="error" sx={{ mb: 2 }}>Invalid JSON: {jsonError}</Alert> : null}
            <TextField
              multiline
              fullWidth
              value={jsonText}
              onChange={(event) => {
                setJsonText(event.target.value)
                try {
                  const parsed = JSON.parse(event.target.value) as JsonObject
                  setConfigJson(parsed)
                  setJsonError(null)
                } catch (error) {
                  setJsonError(error instanceof Error ? error.message : 'Invalid JSON')
                }
              }}
              sx={{ '& .MuiInputBase-root': { minHeight: 520, alignItems: 'flex-start' }, '& textarea': { fontFamily: 'monospace', minHeight: '520px !important' } }}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={11}>
            {!validationResult ? (
              <Typography color="text.secondary">Validate the current draft to see errors and warnings before saving.</Typography>
            ) : (
              <Stack spacing={3}>
                <Alert severity={validationResult.valid ? 'success' : 'error'}>
                  {validationResult.valid ? 'Draft configuration is valid.' : 'Draft configuration has validation errors.'}
                </Alert>
                {validationResult.errors.map((issue, index) => (
                  <Alert key={`${issue.code}-${index}`} severity="error" variant="outlined">[{issue.code}] {issue.message}</Alert>
                ))}
                {validationResult.warnings.map((issue, index) => (
                  <Alert key={`${issue.code}-${index}`} severity="warning" variant="outlined">[{issue.code}] {issue.message}</Alert>
                ))}
              </Stack>
            )}
          </TabPanel>
        </Box>
      </Card>

      <Box sx={{ mt: 2, p: 2, border: '1px solid', borderColor: 'border.default', borderRadius: 2, display: 'flex', justifyContent: 'space-between', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">Form + JSON stay in sync, and saving preserves the old version.</Typography>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<X size={16} />} onClick={onBack}>Discard</Button>
          <Button variant="contained" startIcon={<Save size={16} />} disabled={!!jsonError || createVersionMutation.isPending || updateStrategyMutation.isPending} onClick={handleSave}>
            {createVersionMutation.isPending || updateStrategyMutation.isPending ? 'Saving...' : 'Save as New Version'}
          </Button>
        </Stack>
      </Box>
    </Box>
  )
}

export default function StrategyEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: strategy, isLoading: isLoadingStrategy } = useStrategy(id ?? '')
  const { data: versions, isLoading: isLoadingVersions } = useStrategyVersions(id ?? '')

  if (isLoadingStrategy || isLoadingVersions) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}><CircularProgress /></Box>
  }

  if (!strategy) {
    return <Typography>Strategy not found</Typography>
  }

  return (
    <StrategyEditForm
      key={`${strategy.id}:${versions?.[0]?.id ?? 'none'}`}
      strategy={strategy}
      versions={versions ?? []}
      onBack={() => navigate(`/strategies/${strategy.id}`)}
      onSaved={() => navigate(`/strategies/${strategy.id}`)}
    />
  )
}
