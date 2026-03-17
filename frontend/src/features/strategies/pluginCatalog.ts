export type BuiltinPluginFieldKind = 'select' | 'integer' | 'number' | 'boolean'
export type BuiltinPluginFieldDisplay = 'raw' | 'percent' | 'boolean'

export interface BuiltinPluginFieldOption {
  label: string
  value: string
}

export interface BuiltinPluginFieldDefinition {
  key: string
  label: string
  kind: BuiltinPluginFieldKind
  helperText: string
  step?: number
  display?: BuiltinPluginFieldDisplay
  options?: readonly BuiltinPluginFieldOption[]
  summary?: boolean
}

export interface BuiltinPluginOption {
  value: string
  label: string
  version: string
  description: string
  defaultConfig: Record<string, string | number | boolean>
  fields: readonly BuiltinPluginFieldDefinition[]
}

const DEFAULT_TIMEFRAME_OPTIONS = [
  { value: '1m', label: '1m' },
  { value: '5m', label: '5m' },
  { value: '15m', label: '15m' },
  { value: '1h', label: '1h' },
] as const

export const DEFAULT_PLUGIN_VERSION = '1.0.0'

export const BUILTIN_PLUGIN_OPTIONS: readonly BuiltinPluginOption[] = [
  {
    value: 'breakout_v1',
    label: 'Breakout V1',
    version: '1.0.0',
    description: '최근 N개 봉의 최고 종가를 돌파하면 진입하고, 최저 종가를 이탈하면 청산하는 샘플 플러그인입니다.',
    defaultConfig: {
      timeframe: '5m',
      lookback: 20,
      breakout_pct: 0,
      exit_breakdown_pct: 0.02,
    },
    fields: [
      {
        key: 'timeframe',
        label: '기준 타임프레임',
        kind: 'select',
        helperText: '신호를 계산할 캔들 기준입니다.',
        options: DEFAULT_TIMEFRAME_OPTIONS,
        summary: true,
      },
      {
        key: 'lookback',
        label: '룩백 봉 수',
        kind: 'integer',
        helperText: '최근 몇 개 봉의 최고/최저 종가를 기준으로 볼지 설정합니다.',
        step: 1,
        summary: true,
      },
      {
        key: 'breakout_pct',
        label: '진입 돌파 비율',
        kind: 'number',
        helperText: '0.02면 최근 최고 종가보다 2% 위에서 진입합니다.',
        step: 0.001,
        display: 'percent',
        summary: true,
      },
      {
        key: 'exit_breakdown_pct',
        label: '청산 이탈 비율',
        kind: 'number',
        helperText: '0이면 최근 최저 종가 이탈 즉시 청산합니다.',
        step: 0.001,
        display: 'percent',
        summary: true,
      },
    ],
  },
  {
    value: 'smc_confluence_v1',
    label: 'SMC Confluence V1',
    version: '1.0.0',
    description: '추세 맥락, 오더블럭, FVG 리테스트가 겹칠 때 진입하고 구조가 깨지면 청산하는 long-only confluence 플러그인입니다.',
    defaultConfig: {
      timeframe: '5m',
      trend_lookback: 12,
      order_block_lookback: 8,
      displacement_min_body_ratio: 0.55,
      displacement_min_pct: 0.003,
      fvg_gap_pct: 0.001,
      zone_retest_tolerance_pct: 0.0015,
      exit_zone_break_pct: 0.002,
      min_confluence_score: 3,
      require_order_block: false,
      require_fvg: false,
      require_confirmation: true,
    },
    fields: [
      {
        key: 'timeframe',
        label: '기준 타임프레임',
        kind: 'select',
        helperText: '추세 맥락과 존 리테스트를 읽을 캔들 기준입니다.',
        options: DEFAULT_TIMEFRAME_OPTIONS,
        summary: true,
      },
      {
        key: 'trend_lookback',
        label: '추세 룩백 봉 수',
        kind: 'integer',
        helperText: '최근 몇 개 봉으로 상승 구조와 추세 맥락을 판정할지 정합니다.',
        step: 1,
        summary: true,
      },
      {
        key: 'order_block_lookback',
        label: '오더블럭 탐색 길이',
        kind: 'integer',
        helperText: '최근 몇 개 봉 안에서 유효한 오더블럭 후보를 찾을지 설정합니다.',
        step: 1,
        summary: true,
      },
      {
        key: 'displacement_min_body_ratio',
        label: '최소 변동성 몸통 비율',
        kind: 'number',
        helperText: '강한 변동 캔들로 볼 최소 몸통 비율입니다. 0.55면 몸통이 전체 레인지의 55% 이상이어야 합니다.',
        step: 0.01,
        display: 'percent',
        summary: true,
      },
      {
        key: 'displacement_min_pct',
        label: '최소 변동 폭',
        kind: 'number',
        helperText: '강한 변동 캔들의 최소 상승 폭입니다. 0.003이면 0.30% 이상 상승해야 합니다.',
        step: 0.001,
        display: 'percent',
        summary: true,
      },
      {
        key: 'fvg_gap_pct',
        label: '최소 FVG 갭 비율',
        kind: 'number',
        helperText: '3캔들 FVG로 인정할 최소 갭 비율입니다.',
        step: 0.001,
        display: 'percent',
        summary: true,
      },
      {
        key: 'zone_retest_tolerance_pct',
        label: '존 리테스트 허용 오차',
        kind: 'number',
        helperText: '오더블럭/FVG 존에 다시 닿았다고 볼 허용 오차입니다.',
        step: 0.001,
        display: 'percent',
        summary: true,
      },
      {
        key: 'exit_zone_break_pct',
        label: '존 이탈 청산 버퍼',
        kind: 'number',
        helperText: '구조 무효화 청산을 낼 때 존 하단 아래로 어느 정도 더 이탈해야 하는지 설정합니다.',
        step: 0.001,
        display: 'percent',
        summary: true,
      },
      {
        key: 'min_confluence_score',
        label: '최소 컨플루언스 점수',
        kind: 'integer',
        helperText: '추세, 오더블럭, FVG, 확인 캔들 중 몇 개가 겹쳐야 진입할지 정합니다.',
        step: 1,
        summary: true,
      },
      {
        key: 'require_order_block',
        label: '오더블럭 필수',
        kind: 'boolean',
        helperText: '항상 오더블럭 리테스트가 동반되어야만 진입하도록 강제합니다.',
        display: 'boolean',
      },
      {
        key: 'require_fvg',
        label: 'FVG 필수',
        kind: 'boolean',
        helperText: '항상 FVG 리테스트가 동반되어야만 진입하도록 강제합니다.',
        display: 'boolean',
      },
      {
        key: 'require_confirmation',
        label: '확인 캔들 필수',
        kind: 'boolean',
        helperText: '반등 확인용 bullish confirmation candle이 있어야만 진입합니다.',
        display: 'boolean',
      },
    ],
  },
] as const

export const DEFAULT_PLUGIN_ID = BUILTIN_PLUGIN_OPTIONS[0].value

export function getBuiltinPluginOption(pluginId: string) {
  return BUILTIN_PLUGIN_OPTIONS.find((option) => option.value === pluginId)
}

export function getBuiltinPluginSummaryFields(pluginId: string) {
  return getBuiltinPluginOption(pluginId)?.fields.filter((field) => field.summary) ?? []
}

export function formatBuiltinPluginConfigValue(field: BuiltinPluginFieldDefinition, value: unknown): string {
  if (field.display === 'boolean' || field.kind === 'boolean') {
    return value === true ? '사용' : '미사용'
  }
  if (field.display === 'percent') {
    return typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '-'
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value.toLocaleString('ko-KR') : value.toString()
  }
  if (typeof value === 'string' && value.trim()) {
    return value
  }
  return '-'
}
