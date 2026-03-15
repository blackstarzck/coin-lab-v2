import { Box, Divider, Stack, Switch, Typography } from '@mui/material'
import { useMemo, useState, type ReactNode } from 'react'

type JsonObject = Record<string, unknown>

interface StrategyExplainPanelProps {
  signals: unknown[]
  selectedSignalId: string | null
  onSelectSignal: (signalId: string) => void
  strategyConfig?: Record<string, unknown> | null
}

interface RuleDetail {
  label: string
  value: string
}

interface RuleNode {
  id: string
  kind: 'logic' | 'leaf'
  title: string
  subtitle?: string
  summary: string
  expression: string
  details: RuleDetail[]
  children: RuleNode[]
  order?: number
}

interface RuleRow {
  id: string
  title: string
  subtitle?: string
  summary: string
  expression: string
}

type ViewMode = 'view' | 'code'
type SectionKey = 'entry' | 'reentry' | 'exit'

const CONDITION_TYPE_LABELS: Record<string, string> = {
  indicator_compare: '지표 비교',
  threshold_compare: '임계값 비교',
  cross_over: '상향 돌파',
  cross_under: '하향 돌파',
  price_breakout: '가격 돌파',
  volume_spike: '거래량 급증',
  rsi_range: 'RSI 범위',
  candle_pattern: '캔들 패턴',
  regime_match: '장세 조건',
}

const OPERATOR_LABELS: Record<string, string> = {
  '>': '초과',
  '>=': '이상',
  '<': '미만',
  '<=': '이하',
  '==': '같음',
  '!=': '다름',
}

const PRICE_FIELD_LABELS: Record<string, string> = {
  open: '시가',
  high: '고가',
  low: '저가',
  close: '종가',
  volume: '거래량',
}

const INDICATOR_LABELS: Record<string, string> = {
  ema: 'EMA',
  sma: 'SMA',
  rsi: 'RSI',
  macd: 'MACD',
}

const PATTERN_LABELS: Record<string, string> = {
  bullish_engulfing: '상승 장악형',
  bearish_engulfing: '하락 장악형',
  inside_bar_break: '인사이드 바 돌파',
  long_lower_wick: '긴 아래꼬리',
}

const REGIME_LABELS: Record<string, string> = {
  trend_up: '상승 추세',
  trend_down: '하락 추세',
  range: '횡보',
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

function asNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function toTitleCase(text: string): string {
  return text
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatValue(value: unknown): string {
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 6 })
  }
  if (typeof value === 'boolean') {
    return value ? '예' : '아니오'
  }
  if (value == null) {
    return '-'
  }
  return String(value)
}

function formatCodeValue(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? String(value) : value.toString()
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (value == null) {
    return 'null'
  }
  return String(value)
}

function formatSourceCode(ref: JsonObject): string {
  const kind = asString(ref.kind).toLowerCase()
  const params = asObject(ref.params)
  const paramEntries = Object.entries(params)
    .filter(([, value]) => value != null)
    .map(([key, value]) => `${key}=${formatCodeValue(value)}`)
  const paramText = paramEntries.length > 0 ? `(${paramEntries.join(', ')})` : ''

  if (kind === 'price') {
    return `price.${asString(ref.field, 'close')}`
  }

  if (kind === 'indicator' || kind === 'derived') {
    const name = asString(ref.name, kind || 'value')
    return `${name}${paramText}`
  }

  if (kind === 'constant') {
    return formatCodeValue(ref.value)
  }

  return kind ? `${kind}${paramText}` : 'value'
}

function formatSourceHuman(ref: JsonObject): string {
  const kind = asString(ref.kind).toLowerCase()
  const params = asObject(ref.params)

  if (kind === 'price') {
    return PRICE_FIELD_LABELS[asString(ref.field, 'close').toLowerCase()] ?? asString(ref.field, 'close')
  }

  if (kind === 'indicator') {
    const name = INDICATOR_LABELS[asString(ref.name, 'indicator').toLowerCase()] ?? asString(ref.name, 'indicator').toUpperCase()
    const length = asNumber(params.length)
    return length != null ? `${name}(${length})` : name
  }

  if (kind === 'derived') {
    const name = asString(ref.name, 'derived').toLowerCase()
    const lookback = asNumber(params.lookback)
    const excludeCurrent = params.exclude_current === true ? ' (현재 봉 제외)' : ''

    if (name === 'highest_high') {
      return lookback != null ? `최근 ${lookback}봉 최고가${excludeCurrent}` : `최근 최고가${excludeCurrent}`
    }
    if (name === 'lowest_low') {
      return lookback != null ? `최근 ${lookback}봉 최저가${excludeCurrent}` : `최근 최저가${excludeCurrent}`
    }
    if (name === 'volume_ratio') {
      return lookback != null ? `거래량 비율(${lookback})` : '거래량 비율'
    }

    return lookback != null ? `${toTitleCase(name)}(${lookback})${excludeCurrent}` : `${toTitleCase(name)}${excludeCurrent}`
  }

  if (kind === 'constant') {
    return formatValue(ref.value)
  }

  return '값'
}

function buildLeafSummary(node: JsonObject): string {
  const type = asString(node.type)
  const operator = asString(node.operator, '>')

  if (type === 'indicator_compare' || type === 'threshold_compare') {
    return `${formatSourceHuman(asObject(node.left))} ${operator} ${formatSourceHuman(asObject(node.right))}`
  }
  if (type === 'cross_over') {
    return `${formatSourceHuman(asObject(node.left))}가 ${formatSourceHuman(asObject(node.right))} 위로 돌파할 때`
  }
  if (type === 'cross_under') {
    return `${formatSourceHuman(asObject(node.left))}가 ${formatSourceHuman(asObject(node.right))} 아래로 이탈할 때`
  }
  if (type === 'price_breakout') {
    return `${formatSourceHuman(asObject(node.source))} ${operator} ${formatSourceHuman(asObject(node.reference))}`
  }
  if (type === 'volume_spike') {
    return `${formatSourceHuman(asObject(node.source))} ${asString(node.operator, '>=')} ${formatValue(node.threshold)}`
  }
  if (type === 'rsi_range') {
    return `${formatSourceHuman(asObject(node.source))}가 ${formatValue(node.min)} ~ ${formatValue(node.max)} 범위일 때`
  }
  if (type === 'candle_pattern') {
    return `${PATTERN_LABELS[asString(node.pattern)] ?? toTitleCase(asString(node.pattern, 'pattern'))} 패턴이 나올 때`
  }
  if (type === 'regime_match') {
    return `장세가 ${REGIME_LABELS[asString(node.regime)] ?? toTitleCase(asString(node.regime, 'regime'))}일 때`
  }

  return CONDITION_TYPE_LABELS[type] ?? type
}

function buildLeafExpression(node: JsonObject): string {
  const type = asString(node.type)
  const operator = asString(node.operator, '>')

  if (type === 'indicator_compare' || type === 'threshold_compare') {
    return `${formatSourceCode(asObject(node.left))} ${operator} ${formatSourceCode(asObject(node.right))}`
  }
  if (type === 'cross_over') {
    return `cross_over(${formatSourceCode(asObject(node.left))}, ${formatSourceCode(asObject(node.right))})`
  }
  if (type === 'cross_under') {
    return `cross_under(${formatSourceCode(asObject(node.left))}, ${formatSourceCode(asObject(node.right))})`
  }
  if (type === 'price_breakout') {
    return `${formatSourceCode(asObject(node.source))} ${operator} ${formatSourceCode(asObject(node.reference))}`
  }
  if (type === 'volume_spike') {
    return `${formatSourceCode(asObject(node.source))} ${asString(node.operator, '>=')} ${formatCodeValue(node.threshold)}`
  }
  if (type === 'rsi_range') {
    return `${formatSourceCode(asObject(node.source))} in [${formatCodeValue(node.min)}, ${formatCodeValue(node.max)}]`
  }
  if (type === 'candle_pattern') {
    const timeframe = asString(node.timeframe)
    return timeframe ? `candle_pattern(pattern=${asString(node.pattern, 'pattern')}, timeframe=${timeframe})` : `candle_pattern(pattern=${asString(node.pattern, 'pattern')})`
  }
  if (type === 'regime_match') {
    return `regime == ${asString(node.regime, 'regime')}`
  }

  return asString(node.type, 'condition')
}

function buildLeafDetails(node: JsonObject): RuleDetail[] {
  const type = asString(node.type)
  const operator = asString(node.operator, '>')

  if (type === 'indicator_compare' || type === 'threshold_compare') {
    return [
      { label: '왼쪽 기준', value: formatSourceHuman(asObject(node.left)) },
      { label: '비교', value: `${OPERATOR_LABELS[operator] ?? operator} (${operator})` },
      { label: '오른쪽 기준', value: formatSourceHuman(asObject(node.right)) },
    ]
  }

  if (type === 'cross_over' || type === 'cross_under') {
    const details: RuleDetail[] = [
      { label: '기준 A', value: formatSourceHuman(asObject(node.left)) },
      { label: '기준 B', value: formatSourceHuman(asObject(node.right)) },
    ]
    const lookbackBars = asNumber(node.lookback_bars)
    if (lookbackBars != null) {
      details.push({ label: '돌파 확인 봉 수', value: `${lookbackBars}` })
    }
    return details
  }

  if (type === 'price_breakout') {
    return [
      { label: '대상 값', value: formatSourceHuman(asObject(node.source)) },
      { label: '비교', value: `${OPERATOR_LABELS[operator] ?? operator} (${operator})` },
      { label: '비교 기준', value: formatSourceHuman(asObject(node.reference)) },
    ]
  }

  if (type === 'volume_spike') {
    return [
      { label: '관측 값', value: formatSourceHuman(asObject(node.source)) },
      { label: '비교', value: `${OPERATOR_LABELS[operator] ?? operator} (${operator})` },
      { label: '임계값', value: formatValue(node.threshold) },
    ]
  }

  if (type === 'rsi_range') {
    return [
      { label: '관측 값', value: formatSourceHuman(asObject(node.source)) },
      { label: '최솟값', value: formatValue(node.min) },
      { label: '최댓값', value: formatValue(node.max) },
    ]
  }

  if (type === 'candle_pattern') {
    return [
      { label: '패턴', value: PATTERN_LABELS[asString(node.pattern)] ?? toTitleCase(asString(node.pattern, 'pattern')) },
      { label: '타임프레임', value: asString(node.timeframe, '-') },
    ]
  }

  if (type === 'regime_match') {
    return [{ label: '장세', value: REGIME_LABELS[asString(node.regime)] ?? toTitleCase(asString(node.regime, 'regime')) }]
  }

  return []
}

function buildRuleNode(node: JsonObject, path: string, leafCounter: { current: number }, verb: '매수' | '매도'): RuleNode | null {
  const logic = asString(node.logic).toLowerCase()

  if (logic === 'all' || logic === 'any') {
    const children = asArray(node.conditions)
      .map((child, index) => buildRuleNode(asObject(child), `${path}.conditions[${index}]`, leafCounter, verb))
      .filter((child): child is RuleNode => child != null)

    return {
      id: path,
      kind: 'logic',
      title: logic === 'all' ? `${verb} 조건 조합` : `${verb} 조건 그룹`,
      subtitle: undefined,
      summary: '',
      expression: '',
      details: [],
      children,
    }
  }

  if (logic === 'not') {
    const child = buildRuleNode(asObject(node.condition), `${path}.condition`, leafCounter, verb)
    return {
      id: path,
      kind: 'logic',
      title: `${verb} 조건 그룹`,
      subtitle: undefined,
      summary: '',
      expression: '',
      details: [],
      children: child ? [child] : [],
    }
  }

  const type = asString(node.type)
  if (!type) {
    return null
  }

  const order = ++leafCounter.current
  return {
    id: path,
    kind: 'leaf',
    title: `조건 ${order}`,
    subtitle: CONDITION_TYPE_LABELS[type] ?? type,
    summary: buildLeafSummary(node),
    expression: buildLeafExpression(node),
    details: buildLeafDetails(node),
    children: [],
    order,
  }
}

function SectionBlock({
  title,
  subtitle,
  action,
  children,
}: {
  title: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
}) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1.5}>
        <Stack spacing={0.35}>
          <Typography variant="subtitle2" fontWeight={500}>
            {title}
          </Typography>
          {subtitle ? (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          ) : null}
        </Stack>
        {action}
      </Stack>
      {children}
    </Box>
  )
}

function SectionModeSwitch({
  sectionTitle,
  mode,
  onChange,
}: {
  sectionTitle: string
  mode: ViewMode
  onChange: (mode: ViewMode) => void
}) {
  const isCode = mode === 'code'

  return (
    <Stack direction="row" spacing={0.5} alignItems="center" sx={{ flexShrink: 0 }}>
      <Typography variant="caption" color={isCode ? 'text.secondary' : 'text.primary'}>
        view
      </Typography>
      <Switch
        size="small"
        checked={isCode}
        onChange={(event) => onChange(event.target.checked ? 'code' : 'view')}
        inputProps={{ 'aria-label': `${sectionTitle} 보기 모드 전환` }}
      />
      <Typography variant="caption" color={isCode ? 'text.primary' : 'text.secondary'}>
        code
      </Typography>
    </Stack>
  )
}

function flattenRuleLeaves(node: RuleNode | null): RuleNode[] {
  if (!node) {
    return []
  }

  if (node.kind === 'leaf') {
    return [node]
  }

  return node.children.flatMap((child) => flattenRuleLeaves(child))
}

function createRuleRow(id: string, title: string, subtitle: string | undefined, summary: string, expression: string): RuleRow {
  return { id, title, subtitle, summary, expression }
}

function buildEntryRows(node: RuleNode | null): RuleRow[] {
  return flattenRuleLeaves(node).map((leaf) => createRuleRow(leaf.id, leaf.title, leaf.subtitle, leaf.summary, leaf.expression))
}

function buildReentryRows(config: JsonObject, resetRule: RuleNode | null): RuleRow[] {
  const rows: RuleRow[] = []
  let settingIndex = 1

  if (typeof config.allow === 'boolean') {
    rows.push(createRuleRow(
      'reentry.allow',
      `설정 ${settingIndex++}`,
      '재진입',
      config.allow ? '재진입을 허용합니다.' : '재진입을 허용하지 않습니다.',
      `allow = ${formatCodeValue(config.allow)}`,
    ))
  }

  const cooldownBars = asNumber(config.cooldown_bars)
  if (cooldownBars != null) {
    rows.push(createRuleRow(
      'reentry.cooldown_bars',
      `설정 ${settingIndex++}`,
      '대기 봉 수',
      `${cooldownBars}봉이 지나야 다시 진입합니다.`,
      `cooldown_bars = ${cooldownBars}`,
    ))
  }

  if (typeof config.require_reset === 'boolean') {
    rows.push(createRuleRow(
      'reentry.require_reset',
      `설정 ${settingIndex++}`,
      '리셋 필요',
      config.require_reset ? '리셋 조건을 만족해야 다시 진입합니다.' : '리셋 조건 없이 다시 진입할 수 있습니다.',
      `require_reset = ${formatCodeValue(config.require_reset)}`,
    ))
  }

  return [
    ...rows,
    ...flattenRuleLeaves(resetRule).map((leaf, index) => createRuleRow(leaf.id, `조건 ${index + 1}`, leaf.subtitle, leaf.summary, leaf.expression)),
  ]
}

function buildExitRows(config: JsonObject, exitRule: RuleNode | null): RuleRow[] {
  const rows: RuleRow[] = []
  let settingIndex = 1

  const stopLossPct = asNumber(config.stop_loss_pct)
  if (stopLossPct != null) {
    rows.push(createRuleRow(
      'exit.stop_loss_pct',
      `설정 ${settingIndex++}`,
      '손절',
      `손실이 ${formatPercent(stopLossPct)} 이상이면 매도합니다.`,
      `stop_loss_pct = ${formatCodeValue(stopLossPct)}`,
    ))
  }

  const takeProfitPct = asNumber(config.take_profit_pct)
  if (takeProfitPct != null) {
    rows.push(createRuleRow(
      'exit.take_profit_pct',
      `설정 ${settingIndex++}`,
      '익절',
      `수익이 ${formatPercent(takeProfitPct)} 이상이면 매도합니다.`,
      `take_profit_pct = ${formatCodeValue(takeProfitPct)}`,
    ))
  }

  const trailingStopPct = asNumber(config.trailing_stop_pct)
  if (trailingStopPct != null) {
    rows.push(createRuleRow(
      'exit.trailing_stop_pct',
      `설정 ${settingIndex++}`,
      '트레일링 스탑',
      `고점 대비 ${formatPercent(trailingStopPct)} 이상 밀리면 매도합니다.`,
      `trailing_stop_pct = ${formatCodeValue(trailingStopPct)}`,
    ))
  }

  const timeStopBars = asNumber(config.time_stop_bars)
  if (timeStopBars != null) {
    rows.push(createRuleRow(
      'exit.time_stop_bars',
      `설정 ${settingIndex++}`,
      '시간 기반 청산',
      `${timeStopBars}봉이 지나면 매도합니다.`,
      `time_stop_bars = ${timeStopBars}`,
    ))
  }

  asArray(config.partial_take_profits).forEach((item, index) => {
    const partial = asObject(item)
    const atProfitPct = asNumber(partial.at_profit_pct)
    const closeRatio = asNumber(partial.close_ratio)

    rows.push(createRuleRow(
      `exit.partial_take_profits.${index}`,
      `설정 ${settingIndex++}`,
      '분할 익절',
      atProfitPct != null && closeRatio != null
        ? `수익이 ${formatPercent(atProfitPct)} 이상이면 보유량의 ${formatPercent(closeRatio)}를 매도합니다.`
        : '분할 익절 규칙이 설정되어 있습니다.',
      atProfitPct != null && closeRatio != null
        ? `partial_take_profits[${index}] = { at_profit_pct: ${formatCodeValue(atProfitPct)}, close_ratio: ${formatCodeValue(closeRatio)} }`
        : `partial_take_profits[${index}] = configured`,
    ))
  })

  return [
    ...rows,
    ...flattenRuleLeaves(exitRule).map((leaf, index) => createRuleRow(leaf.id, `조건 ${index + 1}`, leaf.subtitle, leaf.summary, leaf.expression)),
  ]
}

function RuleTable({
  rows,
  emptyText,
  mode,
}: {
  rows: RuleRow[]
  emptyText: string
  mode: ViewMode
}) {
  if (rows.length === 0) {
    return (
      <Typography variant="caption" color="text.secondary">
        {emptyText}
      </Typography>
    )
  }

  return (
    <Box
      sx={{
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: '72px 110px minmax(0, 1fr)',
          gap: 1,
          px: 1.25,
          py: 0.875,
          bgcolor: 'rgba(255, 255, 255, 0.03)',
        }}
      >
        <Typography variant="caption" color="text.secondary">조건</Typography>
        <Typography variant="caption" color="text.secondary">유형</Typography>
        <Typography variant="caption" color="text.secondary">{mode === 'view' ? '실행 기준' : '코드 조건'}</Typography>
      </Box>
      <Divider />
      <Stack divider={<Divider flexItem />}>
        {rows.map((row) => (
          <Box
            key={row.id}
            sx={{
              display: 'grid',
              gridTemplateColumns: '72px 110px minmax(0, 1fr)',
              gap: 1,
              px: 1.25,
              py: 1,
              alignItems: 'start',
            }}
          >
            <Typography variant="caption" fontWeight={500}>
              {row.title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {row.subtitle ?? '-'}
            </Typography>
            <Typography
              variant="caption"
              sx={mode === 'code' ? { fontFamily: 'Consolas, "SFMono-Regular", Menlo, monospace', letterSpacing: '-0.01em' } : undefined}
            >
              {mode === 'view' ? row.summary : row.expression}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Box>
  )
}

export function StrategyExplainPanel({ strategyConfig }: StrategyExplainPanelProps) {
  const config = asObject(strategyConfig)
  const [sectionModes, setSectionModes] = useState<Record<SectionKey, ViewMode>>({
    entry: 'view',
    reentry: 'view',
    exit: 'view',
  })

  const entryRule = useMemo(() => {
    const counter = { current: 0 }
    return buildRuleNode(asObject(config.entry), 'entry', counter, '매수')
  }, [config.entry])

  const reentryConfig = asObject(config.reentry)
  const reentryRule = useMemo(() => {
    if (!reentryConfig.reset_condition) {
      return null
    }
    const counter = { current: 0 }
    return buildRuleNode(asObject(reentryConfig.reset_condition), 'reentry.reset_condition', counter, '매수')
  }, [reentryConfig.reset_condition])

  const exitConfig = asObject(config.exit)
  const exitRule = useMemo(() => {
    const counter = { current: 0 }
    return buildRuleNode(exitConfig, 'exit', counter, '매도')
  }, [exitConfig])

  const entryRows = useMemo(() => buildEntryRows(entryRule), [entryRule])
  const reentryRows = useMemo(() => buildReentryRows(reentryConfig, reentryRule), [reentryConfig, reentryRule])
  const exitRows = useMemo(() => buildExitRows(exitConfig, exitRule), [exitConfig, exitRule])

  const handleSectionModeChange = (section: SectionKey, mode: ViewMode) => {
    setSectionModes((current) => (current[section] === mode ? current : { ...current, [section]: mode }))
  }

  if (Object.keys(config).length === 0) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="text.secondary">전략 설정이 없어 해설을 표시할 수 없습니다.</Typography>
      </Box>
    )
  }

  return (
    <Stack
      spacing={2.5}
      divider={<Divider flexItem />}
      sx={{
        p: 2,
        '& .MuiTypography-root': {
          fontWeight: 500,
        },
      }}
    >
      <SectionBlock
        title="진입 규칙"
        action={<SectionModeSwitch sectionTitle="진입 규칙" mode={sectionModes.entry} onChange={(mode) => handleSectionModeChange('entry', mode)} />}
      >
        <RuleTable rows={entryRows} emptyText="정의된 진입 조건이 없습니다." mode={sectionModes.entry} />
      </SectionBlock>

      <SectionBlock
        title="재진입 규칙"
        action={<SectionModeSwitch sectionTitle="재진입 규칙" mode={sectionModes.reentry} onChange={(mode) => handleSectionModeChange('reentry', mode)} />}
      >
        <RuleTable rows={reentryRows} emptyText="정의된 재진입 규칙이 없습니다." mode={sectionModes.reentry} />
      </SectionBlock>

      <SectionBlock
        title="청산 규칙"
        action={<SectionModeSwitch sectionTitle="청산 규칙" mode={sectionModes.exit} onChange={(mode) => handleSectionModeChange('exit', mode)} />}
      >
        <RuleTable rows={exitRows} emptyText="정의된 청산 규칙이 없습니다." mode={sectionModes.exit} />
      </SectionBlock>
    </Stack>
  )
}
