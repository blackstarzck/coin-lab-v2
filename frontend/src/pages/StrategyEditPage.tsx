import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
  Card,
  Checkbox,
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
  Tooltip,
  Typography,
} from '@mui/material'
import { ArrowLeft, Save, X } from 'lucide-react'

import {
  useCreateStrategy,
  useCreateStrategyVersion,
  useStrategy,
  useStrategyVersions,
  useUpdateStrategy,
  useValidateDraft,
  useValidateVersion,
} from '@/features/strategies/api'
import type { UniverseCatalogItem } from '@/features/universe/api'
import { useUniverseCatalog } from '@/features/universe/api'
import { ConditionEditor, defaultConditionNode } from '@/features/strategies/ConditionEditor'
import { createDefaultStrategyConfig, DEFAULT_STRATEGY_NAME } from '@/features/strategies/defaultStrategyConfig'
import type { Strategy, StrategyVersion, ValidationResult } from '@/entities/strategy/types'
import { MuiNumberField } from '@/shared/ui/MuiNumberField'

type JsonObject = Record<string, unknown>
const DEFAULT_STRATEGY_SYMBOLS = ['KRW-BTC']
const DEFAULT_INITIAL_CAPITAL = 1_000_000
const DEFAULT_POSITION_CONFIG: JsonObject = {
  max_open_positions_per_symbol: 1,
  allow_scale_in: false,
  size_mode: 'fixed_percent',
  size_value: 0.1,
  max_concurrent_positions: 4,
}
const DEFAULT_BACKTEST_CONFIG: JsonObject = {
  initial_capital: DEFAULT_INITIAL_CAPITAL,
  fee_bps: 5,
  slippage_bps: 3,
  latency_ms: 200,
  fill_assumption: 'next_bar_open',
}
const STRATEGY_TYPE_OPTIONS = [
  {
    value: 'dsl',
    label: '규칙식',
    description: '조건 편집기에서 진입과 청산 규칙을 직접 조합하는 기본 전략 유형입니다.',
  },
  {
    value: 'plugin',
    label: '플러그인',
    description: '코드로 구현된 전략 로직을 연결해 실행하는 유형입니다.',
  },
  {
    value: 'hybrid',
    label: '하이브리드',
    description: '규칙식 설정과 플러그인 로직을 함께 사용하는 혼합형 전략 유형입니다.',
  },
] as const

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

function normalizeSymbolList(value: unknown, fallback = DEFAULT_STRATEGY_SYMBOLS): string[] {
  const seen = new Set<string>()
  const normalized = asArray(value)
    .map((item) => item.trim().toUpperCase())
    .filter((item) => {
      if (!item || seen.has(item)) {
        return false
      }
      seen.add(item)
      return true
    })
  return normalized.length > 0 ? normalized : [...fallback]
}

function sortSymbols(symbols: string[]): string[] {
  return [...symbols].sort((left, right) => {
    if (left === 'KRW-BTC') return -1
    if (right === 'KRW-BTC') return 1
    return left.localeCompare(right)
  })
}

function formatTurnoverLabel(value: number | null | undefined): string {
  if (!value) {
    return '24시간 거래대금 정보 없음'
  }
  if (value >= 1_000_000_000_000) {
    return `24시간 거래대금 ${(value / 1_000_000_000_000).toFixed(2)}조 원`
  }
  if (value >= 100_000_000) {
    return `24시간 거래대금 ${(value / 100_000_000).toFixed(1)}억 원`
  }
  return `24시간 거래대금 ${Math.round(value).toLocaleString('ko-KR')}원`
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback
}

function coerceNumberValue(value: number | null, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function coerceIntegerValue(value: number | null, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? Math.trunc(value) : fallback
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

function normalizeUniverseConfig(universe: JsonObject): JsonObject {
  const symbols = sortSymbols(normalizeSymbolList(universe.symbols))
  const catalogSymbols = sortSymbols(normalizeSymbolList([...asArray(universe.catalog_symbols), ...symbols], symbols))
  return {
    ...universe,
    mode: 'static',
    symbols,
    catalog_symbols: catalogSymbols,
    max_symbols: symbols.length,
  }
}

function updateUniverseConfig(config: JsonObject, updater: (universe: JsonObject) => JsonObject): JsonObject {
  return updateNestedConfig(config, ['universe'], normalizeUniverseConfig(updater(asObject(config.universe))))
}

function normalizeEditableConfig(config: JsonObject): JsonObject {
  return {
    ...config,
    universe: normalizeUniverseConfig(asObject(config.universe)),
    position: {
      ...DEFAULT_POSITION_CONFIG,
      ...asObject(config.position),
    },
    backtest: {
      ...DEFAULT_BACKTEST_CONFIG,
      ...asObject(config.backtest),
    },
  }
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
  const normalizedBase = normalizeEditableConfig(baseConfig)
  return {
    ...normalizedBase,
    name,
    description,
    labels,
    notes,
  }
}

function normalizeStrategyKey(value: string): string {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
  return normalized || 'strategy'
}

function createDefaultResetCondition(): JsonObject {
  return {
    type: 'threshold_compare',
    left: { kind: 'price', field: 'close' },
    operator: '<',
    right: {
      kind: 'derived',
      name: 'highest_high',
      params: { lookback: 20, exclude_current: true },
    },
  }
}

function TabPanel({ children, value, index }: { children?: ReactNode, value: number, index: number }) {
  return (
    <div hidden={value !== index} style={{ height: '100%' }}>
      {value === index ? <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>{children}</Box> : null}
    </div>
  )
}

const CONDITION_TAB_CONTENT_SX = {
  width: '100%',
  maxWidth: 1240,
  mr: 'auto',
} as const

function StrategyEditForm({
  mode,
  strategy,
  versions,
  initialConfig,
  onBack,
  onSaved,
}: {
  mode: 'create' | 'edit'
  strategy: Strategy | null
  versions: StrategyVersion[]
  initialConfig: JsonObject
  onBack: () => void
  onSaved: (strategyId: string) => void
}) {
  const latestVersion = versions[0]
  const createStrategyMutation = useCreateStrategy()
  const updateStrategyMutation = useUpdateStrategy()
  const createVersionMutation = useCreateStrategyVersion()
  const validateDraftMutation = useValidateDraft()
  const validateVersionMutation = useValidateVersion()
  const normalizedInitialConfig = normalizeEditableConfig(initialConfig)
  const [symbolSearch, setSymbolSearch] = useState('')
  const deferredSymbolSearch = useDeferredValue(symbolSearch.trim())
  const { data: topTurnoverMarkets = [], isLoading: isTopTurnoverLoading } = useUniverseCatalog({ limit: 10 })
  const { data: searchResults = [], isLoading: isSearchLoading } = useUniverseCatalog({
    query: deferredSymbolSearch,
    limit: 20,
    enabled: deferredSymbolSearch.length > 0,
  })

  const [tabValue, setTabValue] = useState(0)
  const [name, setName] = useState(strategy?.name ?? String(normalizedInitialConfig.name ?? DEFAULT_STRATEGY_NAME))
  const [description, setDescription] = useState(strategy?.description ?? String(normalizedInitialConfig.description ?? ''))
  const [labelsText, setLabelsText] = useState(strategy?.labels.join(', ') ?? asArray(normalizedInitialConfig.labels).join(', '))
  const [notes, setNotes] = useState(latestVersion?.notes ?? '')
  const [configJson, setConfigJson] = useState<JsonObject>(normalizedInitialConfig)
  const [jsonText, setJsonText] = useState(JSON.stringify(normalizedInitialConfig, null, 2))
  const [jsonError, setJsonError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)
  const [saveError, setSaveError] = useState<string | null>(null)

  const labels = useMemo(() => labelsText.split(',').map((item) => item.trim()).filter(Boolean), [labelsText])
  const strategyKey = String(configJson.id ?? strategy?.strategy_key ?? '')
  const strategyType = String(configJson.type ?? strategy?.strategy_type ?? 'dsl')
  const diffRows = useMemo(
    () => buildDiffRows(normalizedInitialConfig, configJson),
    [normalizedInitialConfig, configJson],
  )
  const strategyTypeHelpTooltip = (
    <Stack spacing={1.1} sx={{ maxWidth: 300, py: 0.25 }}>
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
        전략 유형 안내
      </Typography>
      {STRATEGY_TYPE_OPTIONS.map((option) => (
        <Box key={option.value}>
          <Typography variant="body2" sx={{ fontWeight: 700, lineHeight: 1.35 }}>
            {option.label}
          </Typography>
          <Typography variant="caption" sx={{ display: 'block', color: 'rgba(255, 255, 255, 0.74)', lineHeight: 1.45 }}>
            {option.description}
          </Typography>
        </Box>
      ))}
    </Stack>
  )

  const market = asObject(configJson.market)
  const universe = asObject(configJson.universe)
  const selectedSymbols = sortSymbols(normalizeSymbolList(universe.symbols))
  const addedSymbols = sortSymbols(normalizeSymbolList(universe.catalog_symbols, selectedSymbols))
  const reentry = asObject(configJson.reentry)
  const position = asObject(configJson.position)
  const exitConfig = asObject(configJson.exit)
  const risk = asObject(configJson.risk)
  const execution = asObject(configJson.execution)
  const backtest = asObject(configJson.backtest)
  const catalogInfoMap = useMemo(() => {
    const map = new Map<string, UniverseCatalogItem>()
    for (const item of [...topTurnoverMarkets, ...searchResults]) {
      map.set(item.symbol, item)
    }
    return map
  }, [searchResults, topTurnoverMarkets])

  const updateConfigAtPath = (path: string[], value: unknown) => {
    setConfigJson((prev) => updateNestedConfig(prev, path, value))
  }

  const updateIntegerAtPath = (path: string[], fallback = 0) => (value: number | null) => {
    updateConfigAtPath(path, coerceIntegerValue(value, fallback))
  }

  const updateNumberAtPath = (path: string[], fallback = 0) => (value: number | null) => {
    updateConfigAtPath(path, coerceNumberValue(value, fallback))
  }

  const handleAddCatalogSymbol = (symbol: string) => {
    setConfigJson((prev) => updateUniverseConfig(prev, (currentUniverse) => ({
      ...currentUniverse,
      catalog_symbols: [...asArray(currentUniverse.catalog_symbols), symbol],
    })))
  }

  const handleRemoveCatalogSymbol = (symbol: string) => {
    setConfigJson((prev) => updateUniverseConfig(prev, (currentUniverse) => ({
      ...currentUniverse,
      symbols: asArray(currentUniverse.symbols).filter((item) => String(item).trim().toUpperCase() !== symbol),
      catalog_symbols: asArray(currentUniverse.catalog_symbols).filter((item) => String(item).trim().toUpperCase() !== symbol),
    })))
  }

  const handleToggleSymbol = (symbol: string) => {
    setConfigJson((prev) => updateUniverseConfig(prev, (currentUniverse) => {
      const currentSelected = normalizeSymbolList(currentUniverse.symbols)
      const nextSymbols = currentSelected.includes(symbol)
        ? currentSelected.filter((item) => item !== symbol)
        : [...currentSelected, symbol]
      return {
        ...currentUniverse,
        symbols: nextSymbols,
        catalog_symbols: [...asArray(currentUniverse.catalog_symbols), symbol],
      }
    }))
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
      const normalizedStrategyType = strategyType === 'plugin' || strategyType === 'hybrid' ? strategyType : 'dsl'
      const normalizedStrategyKey = strategyKey.trim() || strategy?.strategy_key || normalizeStrategyKey(name)
      const draftConfig = {
        ...buildDraftConfig(configJson, name, description, labels, notes),
        id: normalizedStrategyKey,
        type: normalizedStrategyType,
      }

      let targetStrategyId = strategy?.id ?? null
      if (mode === 'create') {
        const createdStrategy = await createStrategyMutation.mutateAsync({
          strategy_key: normalizedStrategyKey,
          name,
          strategy_type: normalizedStrategyType,
          description,
          labels,
        })
        targetStrategyId = createdStrategy.id
      } else if (
        strategy
        && (
          strategy.name !== name
          || (strategy.description ?? '') !== description
          || JSON.stringify(strategy.labels) !== JSON.stringify(labels)
        )
      ) {
        await updateStrategyMutation.mutateAsync({ id: strategy.id, name, description, labels })
      }

      if (!targetStrategyId) {
        throw new Error('strategy_id_missing')
      }

      const createdVersion = await createVersionMutation.mutateAsync({
        strategyId: targetStrategyId,
        data: {
          schema_version: String(configJson.schema_version ?? latestVersion?.schema_version ?? '1.0.0'),
          config_json: draftConfig,
          labels,
          notes,
        },
      })
      if (validationResult?.valid) {
        await validateVersionMutation.mutateAsync({ versionId: createdVersion.id, strict: true })
      }
      onSaved(targetStrategyId)
    } catch {
      setSaveError(mode === 'create' ? '전략을 생성하지 못했습니다.' : '전략 버전을 저장하지 못했습니다.')
    }
  }

  return (
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2, flexShrink: 0 }}>
        <IconButton onClick={onBack} sx={{ color: 'text.secondary' }}>
          <ArrowLeft size={20} />
        </IconButton>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h5">{mode === 'create' ? '전략 생성' : `전략 편집: ${strategy?.name ?? ''}`}</Typography>
          <Typography variant="body2" color="text.tertiary">
            {mode === 'create'
              ? '전략 메타데이터와 첫 버전을 함께 생성합니다.'
              : `저장하면 v${latestVersion?.version_no || 1} 기준으로 새 버전이 생성됩니다.`}
          </Typography>
        </Box>
        <Button variant="outlined" onClick={handleValidate} disabled={!!jsonError || validateDraftMutation.isPending}>
          {validateDraftMutation.isPending ? '검증 중...' : '초안 검증'}
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
          <Tab label="기본 정보" />
          <Tab label="마켓 및 유니버스" />
          <Tab label="진입" />
          <Tab label="재진입" />
          <Tab label="포지션" />
          <Tab label="청산" />
          <Tab label="리스크" />
          <Tab label="실행" />
          <Tab label="백테스트" />
          <Tab label={`변경 미리보기 (${diffRows.length})`} />
          <Tab label="원본 설정 편집기" />
          <Tab label={validationResult?.valid ? '검증 완료' : '검증'} />
        </Tabs>

        <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
          <TabPanel value={tabValue} index={0}>
            <Stack spacing={3} maxWidth={760} sx={{ width: '100%', mx: 'auto' }}>
              <TextField
                label="전략 키"
                value={strategyKey}
                onChange={(event) => updateConfigAtPath(['id'], event.target.value)}
                helperText={mode === 'create' ? '전략 키는 전략 규칙 식별자와 전략 식별자로 함께 사용됩니다.' : '기존 전략 키는 생성 이후 변경하지 않습니다.'}
                disabled={mode === 'edit'}
                fullWidth
              />
              <TextField label="전략명" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
              <TextField label="설명" value={description} onChange={(event) => setDescription(event.target.value)} multiline rows={3} fullWidth />
              <TextField label="라벨 (쉼표로 구분)" value={labelsText} onChange={(event) => setLabelsText(event.target.value)} fullWidth />
              <TextField label="버전 노트" value={notes} onChange={(event) => setNotes(event.target.value)} multiline rows={3} fullWidth />
              <FormControl fullWidth disabled={mode === 'edit'}>
                <Tooltip
                  arrow
                  placement="top-start"
                  title={strategyTypeHelpTooltip}
                  slotProps={{
                    tooltip: {
                      sx: {
                        maxWidth: 340,
                      },
                    },
                  }}
                >
                  <InputLabel sx={{ pointerEvents: 'auto', cursor: 'help' }}>전략 유형</InputLabel>
                </Tooltip>
                <Select
                  value={strategyType}
                  label="전략 유형"
                  onChange={(event) => updateConfigAtPath(['type'], event.target.value)}
                >
                  {STRATEGY_TYPE_OPTIONS.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <Grid container spacing={3} maxWidth={840} sx={{ width: '100%', mx: 'auto' }}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>거래소</InputLabel>
                  <Select value={String(market.exchange ?? 'UPBIT')} label="거래소" onChange={(event) => updateConfigAtPath(['market', 'exchange'], event.target.value)}>
                    <MenuItem value="UPBIT">업비트</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>거래 기준</InputLabel>
                  <Select value={String(market.trade_basis ?? 'candle')} label="거래 기준" onChange={(event) => updateConfigAtPath(['market', 'trade_basis'], event.target.value)}>
                    <MenuItem value="candle">캔들</MenuItem>
                    <MenuItem value="tick">틱</MenuItem>
                    <MenuItem value="hybrid">혼합</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="타임프레임"
                  value={asArray(market.timeframes).join(', ')}
                  onChange={(event) => updateConfigAtPath(
                    ['market', 'timeframes'],
                    event.target.value.split(',').map((item) => item.trim()).filter(Boolean),
                  )}
                  helperText="쉼표로 구분해 입력합니다."
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <Stack spacing={1.5}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="subtitle2">거래대금 상위 코인</Typography>
                    <Typography variant="caption" color="text.secondary">
                      상위 10개
                    </Typography>
                  </Box>
                  <Grid container spacing={1.5}>
                    {(topTurnoverMarkets.length > 0 ? topTurnoverMarkets : []).map((item, index) => {
                      const isAdded = addedSymbols.includes(item.symbol)
                      return (
                        <Grid item xs={12} sm={6} md={4} key={item.symbol}>
                          <Card
                            variant="outlined"
                            sx={{
                              borderColor: isAdded ? 'primary.main' : 'divider',
                              bgcolor: isAdded ? 'rgba(0, 200, 120, 0.05)' : 'transparent',
                            }}
                          >
                            <Box sx={{ px: 1.5, py: 1.5 }}>
                              <Stack spacing={1.25}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                                  <Box sx={{ minWidth: 0 }}>
                                    <Typography variant="caption" color="text.secondary">
                                      #{index + 1}
                                    </Typography>
                                    <Typography variant="body2" fontWeight={700}>
                                      {item.symbol}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {item.korean_name}
                                    </Typography>
                                  </Box>
                                  <Button
                                    size="small"
                                    variant={isAdded ? 'outlined' : 'contained'}
                                    disabled={isAdded}
                                    onClick={() => handleAddCatalogSymbol(item.symbol)}
                                  >
                                    {isAdded ? '추가됨' : '추가'}
                                  </Button>
                                </Box>
                                <Typography variant="caption" color="text.secondary">
                                  {formatTurnoverLabel(item.turnover_24h_krw)}
                                </Typography>
                              </Stack>
                            </Box>
                          </Card>
                        </Grid>
                      )
                    })}
                  </Grid>
                  {isTopTurnoverLoading ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={16} />
                      <Typography variant="caption" color="text.secondary">상위 코인 정보를 불러오는 중입니다.</Typography>
                    </Box>
                  ) : null}
                </Stack>
              </Grid>

              <Grid item xs={12}>
                <Stack spacing={1.5}>
                  <Typography variant="subtitle2">코인 검색</Typography>
                  <TextField
                    label="심볼 또는 코인명 검색"
                    value={symbolSearch}
                    onChange={(event) => setSymbolSearch(event.target.value)}
                    helperText="검색 결과에서 먼저 추가한 뒤, 아래 추가한 코인에서 실제 실험 대상으로 선택합니다."
                    fullWidth
                  />
                  {deferredSymbolSearch ? (
                    <Grid container spacing={1.5}>
                      {searchResults.map((item) => {
                        const isAdded = addedSymbols.includes(item.symbol)
                        return (
                          <Grid item xs={12} sm={6} md={4} key={item.symbol}>
                            <Card variant="outlined">
                              <Box sx={{ px: 1.5, py: 1.5 }}>
                                <Stack spacing={1.25}>
                                  <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                                    <Box sx={{ minWidth: 0 }}>
                                      <Typography variant="body2" fontWeight={700}>
                                        {item.symbol}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {item.korean_name} · {item.english_name}
                                      </Typography>
                                    </Box>
                                    <Button
                                      size="small"
                                      variant={isAdded ? 'outlined' : 'contained'}
                                      disabled={isAdded}
                                      onClick={() => handleAddCatalogSymbol(item.symbol)}
                                    >
                                      {isAdded ? '추가됨' : '추가'}
                                    </Button>
                                  </Box>
                                  <Typography variant="caption" color="text.secondary">
                                    {formatTurnoverLabel(item.turnover_24h_krw)}
                                  </Typography>
                                </Stack>
                              </Box>
                            </Card>
                          </Grid>
                        )
                      })}
                    </Grid>
                  ) : (
                    <Typography variant="caption" color="text.secondary">
                      심볼, 한글명, 영문명으로 검색할 수 있습니다.
                    </Typography>
                  )}
                  {deferredSymbolSearch && !isSearchLoading && searchResults.length === 0 ? (
                    <Typography variant="caption" color="text.secondary">
                      검색 결과가 없습니다.
                    </Typography>
                  ) : null}
                  {isSearchLoading ? (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={16} />
                      <Typography variant="caption" color="text.secondary">검색 중입니다.</Typography>
                    </Box>
                  ) : null}
                </Stack>
              </Grid>

              <Grid item xs={12}>
                <Stack spacing={1.5}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="subtitle2">추가한 코인</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {addedSymbols.length}개 추가 / {selectedSymbols.length}개 선택
                    </Typography>
                  </Box>
                  <Grid container spacing={1.5}>
                    {addedSymbols.map((symbol) => {
                      const checked = selectedSymbols.includes(symbol)
                      const item = catalogInfoMap.get(symbol)
                      return (
                        <Grid item xs={12} sm={6} md={4} key={symbol}>
                          <Card
                            variant="outlined"
                            sx={{
                              borderColor: checked ? 'primary.main' : 'divider',
                              bgcolor: checked ? 'rgba(0, 200, 120, 0.08)' : 'transparent',
                              transition: 'border-color 0.2s ease, background-color 0.2s ease',
                            }}
                          >
                            <Box sx={{ px: 1.5, py: 1.5 }}>
                              <Stack spacing={1}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
                                  <Box sx={{ minWidth: 0 }}>
                                    <Typography variant="body2" fontWeight={700}>
                                      {symbol}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {item?.korean_name ?? symbol.replace('KRW-', '')}
                                    </Typography>
                                  </Box>
                                  <IconButton size="small" onClick={() => handleRemoveCatalogSymbol(symbol)}>
                                    <X size={14} />
                                  </IconButton>
                                </Box>
                                <Typography variant="caption" color="text.secondary">
                                  {formatTurnoverLabel(item?.turnover_24h_krw)}
                                </Typography>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                  <Checkbox checked={checked} onChange={() => handleToggleSymbol(symbol)} />
                                  <Typography variant="body2">실험 대상에 포함</Typography>
                                </Box>
                              </Stack>
                            </Box>
                          </Card>
                        </Grid>
                      )
                    })}
                  </Grid>
                  <Typography variant="caption" color="text.secondary">
                    기본 선택은 KRW-BTC입니다. 검색으로 추가한 코인은 저장 후에도 유지되며, 체크된 코인만 실제 실험 대상으로 사용됩니다.
                  </Typography>
                </Stack>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <Stack spacing={2} sx={CONDITION_TAB_CONTENT_SX}>
              <Typography variant="body2" color="text.secondary">
                진입 조건을 구조적으로 편집합니다. 계산에 쓰이는 지표, 조회 봉 수, 기준값 파라미터를 여기서 직접 설정할 수 있습니다.
              </Typography>
              <ConditionEditor
                label="진입 조건"
                value={asObject(configJson.entry).logic || asObject(configJson.entry).type ? asObject(configJson.entry) : defaultConditionNode()}
                onChange={(next) => setConfigJson((prev) => updateNestedConfig(prev, ['entry'], next))}
              />
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={3}>
            <Stack spacing={2} sx={CONDITION_TAB_CONTENT_SX}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={4}>
                  <FormControlLabel
                    control={(
                      <Switch
                        checked={Boolean(reentry.allow)}
                        onChange={(event) => updateConfigAtPath(['reentry', 'allow'], event.target.checked)}
                      />
                    )}
                    label="재진입 허용"
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <MuiNumberField
                    label="재진입 대기 봉 수"
                    fullWidth
                    value={asNumber(reentry.cooldown_bars, 0)}
                    onValueChange={updateIntegerAtPath(['reentry', 'cooldown_bars'], 0)}
                    step={1}
                  />
                </Grid>
                <Grid item xs={12} sm={4}>
                  <FormControlLabel
                    control={(
                      <Switch
                        checked={Boolean(reentry.require_reset)}
                        onChange={(event) => updateConfigAtPath(['reentry', 'require_reset'], event.target.checked)}
                      />
                    )}
                    label="재설정 조건 필요"
                  />
                </Grid>
              </Grid>
              {reentry.allow ? (
                <ConditionEditor
                  label="재설정 조건"
                  value={asObject(reentry.reset_condition).type || asObject(reentry.reset_condition).logic
                    ? asObject(reentry.reset_condition)
                    : createDefaultResetCondition()}
                  onChange={(next) => setConfigJson((prev) => updateNestedConfig(prev, ['reentry', 'reset_condition'], next))}
                />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  재진입이 꺼져 있으면 재설정 조건은 실행되지 않습니다.
                </Typography>
              )}
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={4}>
            <Grid container spacing={3} maxWidth={840} sx={{ width: '100%', mx: 'auto' }}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>포지션 크기 기준</InputLabel>
                  <Select
                    value={String(position.size_mode ?? 'fixed_percent')}
                    label="포지션 크기 기준"
                    onChange={(event) => updateConfigAtPath(['position', 'size_mode'], event.target.value)}
                  >
                    <MenuItem value="fixed_percent">초기 자금 비율</MenuItem>
                    <MenuItem value="fixed_amount">고정 금액 (원)</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label={String(position.size_mode ?? 'fixed_percent') === 'fixed_amount' ? '포지션 금액 (원)' : '포지션 비율 (0~1)'}
                  value={asNumber(position.size_value, 0.1)}
                  onValueChange={updateNumberAtPath(['position', 'size_value'], 0.1)}
                  helperText={String(position.size_mode ?? 'fixed_percent') === 'fixed_amount' ? '주문당 사용할 원화 금액' : '초기 자금 대비 사용할 비율'}
                  fullWidth
                  step={String(position.size_mode ?? 'fixed_percent') === 'fixed_amount' ? 1000 : 0.01}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label="심볼별 최대 보유 포지션"
                  value={asNumber(position.max_open_positions_per_symbol, 1)}
                  onValueChange={updateIntegerAtPath(['position', 'max_open_positions_per_symbol'], 1)}
                  fullWidth
                  step={1}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label="최대 동시 포지션 수"
                  value={asNumber(position.max_concurrent_positions, 4)}
                  onValueChange={updateIntegerAtPath(['position', 'max_concurrent_positions'], 4)}
                  fullWidth
                  step={1}
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel control={<Switch checked={Boolean(position.allow_scale_in)} onChange={(event) => updateConfigAtPath(['position', 'allow_scale_in'], event.target.checked)} />} label="분할 진입 허용" />
              </Grid>
              <Grid item xs={12}>
                <Typography variant="caption" color="text.secondary">
                  초기 자금 기본값은 1,000,000원이며, 포지션 크기는 이 자금을 기준으로 계산됩니다.
                </Typography>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={5}>
            <Stack spacing={2} maxWidth={920} sx={{ width: '100%', mx: 'auto' }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <MuiNumberField
                    label="손절 비율 (%)"
                    fullWidth
                    value={asNumber(exitConfig.stop_loss_pct, 0)}
                    onValueChange={updateNumberAtPath(['exit', 'stop_loss_pct'], 0)}
                    step={0.1}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <MuiNumberField
                    label="익절 비율 (%)"
                    fullWidth
                    value={asNumber(exitConfig.take_profit_pct, 0)}
                    onValueChange={updateNumberAtPath(['exit', 'take_profit_pct'], 0)}
                    step={0.1}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <MuiNumberField
                    label="추적 손절 비율 (%)"
                    fullWidth
                    value={asNumber(exitConfig.trailing_stop_pct, 0)}
                    onValueChange={updateNumberAtPath(['exit', 'trailing_stop_pct'], 0)}
                    step={0.1}
                  />
                </Grid>
                <Grid item xs={12} sm={6}>
                  <MuiNumberField
                    label="시간 제한 봉 수"
                    fullWidth
                    value={asNumber(exitConfig.time_stop_bars, 0)}
                    onValueChange={updateIntegerAtPath(['exit', 'time_stop_bars'], 0)}
                    step={1}
                  />
                </Grid>
              </Grid>
              <ConditionEditor
                label="청산 조건"
                value={exitConfig.logic || exitConfig.type ? exitConfig : defaultConditionNode()}
                onChange={(next) => setConfigJson((prev) => updateNestedConfig(prev, ['exit'], { ...asObject(prev.exit), ...next }))}
              />
              <Typography variant="body2" color="text.secondary">
                퍼센트 기반 청산과 조건 기반 청산을 함께 저장할 수 있습니다. 런타임은 손절, 익절, 추적 손절, 시간 제한과 청산 조건 블록을 모두 평가합니다.
              </Typography>
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={6}>
            <Grid container spacing={3} maxWidth={840} sx={{ width: '100%', mx: 'auto' }}>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label="일일 손실 제한 %"
                  value={asNumber(risk.daily_loss_limit_pct, 0)}
                  onValueChange={updateNumberAtPath(['risk', 'daily_loss_limit_pct'])}
                  fullWidth
                  step={0.1}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label="전략 최대 낙폭 %"
                  value={asNumber(risk.max_strategy_drawdown_pct, 0)}
                  onValueChange={updateNumberAtPath(['risk', 'max_strategy_drawdown_pct'])}
                  fullWidth
                  step={0.1}
                />
              </Grid>
              <Grid item xs={12}>
                <FormControlLabel control={<Switch checked={Boolean(risk.kill_switch_enabled)} onChange={(event) => updateConfigAtPath(['risk', 'kill_switch_enabled'], event.target.checked)} />} label="킬 스위치 활성화" />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={7}>
            <Grid container spacing={3} maxWidth={840} sx={{ width: '100%', mx: 'auto' }}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>진입 주문 유형</InputLabel>
                  <Select value={String(execution.entry_order_type ?? 'market')} label="진입 주문 유형" onChange={(event) => updateConfigAtPath(['execution', 'entry_order_type'], event.target.value)}>
                    <MenuItem value="market">시장가</MenuItem>
                    <MenuItem value="limit">지정가</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>수수료 모델</InputLabel>
                  <Select value={String(execution.fee_model ?? 'per_fill')} label="수수료 모델" onChange={(event) => updateConfigAtPath(['execution', 'fee_model'], event.target.value)}>
                    <MenuItem value="per_fill">체결당</MenuItem>
                    <MenuItem value="per_order">주문당</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={8}>
            <Grid container spacing={3} maxWidth={840} sx={{ width: '100%', mx: 'auto' }}>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label="초기 자본"
                  value={asNumber(backtest.initial_capital, DEFAULT_INITIAL_CAPITAL)}
                  onValueChange={updateNumberAtPath(['backtest', 'initial_capital'], DEFAULT_INITIAL_CAPITAL)}
                  fullWidth
                  step={1000}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <MuiNumberField
                  label="수수료 (0.01% 단위)"
                  value={asNumber(backtest.fee_bps, 5)}
                  onValueChange={updateNumberAtPath(['backtest', 'fee_bps'], 5)}
                  fullWidth
                  step={0.1}
                />
              </Grid>
            </Grid>
          </TabPanel>

          <TabPanel value={tabValue} index={9}>
            <Stack spacing={2}>
              <Typography variant="h6">변경 미리보기</Typography>
              <Typography variant="body2" color="text.secondary">
                {diffRows.length === 0 ? '변경된 항목이 없습니다.' : `${diffRows.length}개 필드가 변경되었습니다.`}
              </Typography>
              {diffRows.map((row) => (
                <Card key={row.path} variant="outlined">
                  <Box sx={{ p: 2 }}>
                    <Typography variant="subtitle2" fontFamily="monospace">{row.path}</Typography>
                    <Grid container spacing={2} sx={{ mt: 0.5 }}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="caption" color="text.secondary">이전 값</Typography>
                        <Box sx={{ mt: 0.5, p: 1.5, borderRadius: 1, bgcolor: 'bg.surface2', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{JSON.stringify(row.before, null, 2)}</Box>
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="caption" color="text.secondary">변경 값</Typography>
                        <Box sx={{ mt: 0.5, p: 1.5, borderRadius: 1, bgcolor: 'rgba(34, 231, 107, 0.05)', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>{JSON.stringify(row.after, null, 2)}</Box>
                      </Grid>
                    </Grid>
                  </Box>
                </Card>
              ))}
            </Stack>
          </TabPanel>

          <TabPanel value={tabValue} index={10}>
            {jsonError ? <Alert severity="error" sx={{ mb: 2 }}>원본 설정 형식 오류: {jsonError}</Alert> : null}
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
                  setJsonError(error instanceof Error ? error.message : '원본 설정 형식 오류')
                }
              }}
              sx={{ '& .MuiInputBase-root': { minHeight: 520, alignItems: 'flex-start' }, '& textarea': { fontFamily: 'monospace', minHeight: '520px !important' } }}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={11}>
            {!validationResult ? (
              <Typography color="text.secondary">저장 전에 현재 초안을 검증해 오류와 경고를 확인하세요.</Typography>
            ) : (
              <Stack spacing={3}>
                <Alert severity={validationResult.valid ? 'success' : 'error'}>
                  {validationResult.valid ? '초안 설정이 유효합니다.' : '초안 설정에 검증 오류가 있습니다.'}
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
        <Typography variant="body2" color="text.secondary">폼과 원본 설정은 동기화되며 저장 시 기존 버전은 유지됩니다.</Typography>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<X size={16} />} onClick={onBack}>취소</Button>
          <Button
            variant="contained"
            startIcon={<Save size={16} />}
            disabled={!!jsonError || createStrategyMutation.isPending || createVersionMutation.isPending || updateStrategyMutation.isPending}
            onClick={handleSave}
          >
            {createStrategyMutation.isPending || createVersionMutation.isPending || updateStrategyMutation.isPending
              ? '저장 중...'
              : (mode === 'create' ? '전략 생성' : '새 버전으로 저장')}
          </Button>
        </Stack>
      </Box>
    </Box>
  )
}

export default function StrategyEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const isCreateMode = !id
  const { data: strategy, isLoading: isLoadingStrategy } = useStrategy(id ?? '')
  const { data: versions, isLoading: isLoadingVersions } = useStrategyVersions(id ?? '')

  if (!isCreateMode && (isLoadingStrategy || isLoadingVersions)) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}><CircularProgress /></Box>
  }

  if (!isCreateMode && !strategy) {
    return <Typography>전략을 찾을 수 없습니다</Typography>
  }

  const createInitialConfig = createDefaultStrategyConfig()

  return (
    <StrategyEditForm
      key={isCreateMode ? 'new-strategy' : `${strategy?.id ?? 'missing'}:${versions?.[0]?.id ?? 'none'}`}
      mode={isCreateMode ? 'create' : 'edit'}
      strategy={strategy ?? null}
      versions={versions ?? []}
      initialConfig={isCreateMode ? createInitialConfig : asObject(versions?.[0]?.config_json)}
      onBack={() => navigate(isCreateMode ? '/strategies' : `/strategies/${strategy?.id ?? ''}`)}
      onSaved={(strategyId) => navigate(`/strategies/${strategyId}`)}
    />
  )
}

