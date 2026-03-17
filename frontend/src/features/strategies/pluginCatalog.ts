export const DEFAULT_PLUGIN_VERSION = '1.0.0'

export const BUILTIN_PLUGIN_OPTIONS = [
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
  },
] as const

export const DEFAULT_PLUGIN_ID = BUILTIN_PLUGIN_OPTIONS[0].value

export function getBuiltinPluginOption(pluginId: string) {
  return BUILTIN_PLUGIN_OPTIONS.find((option) => option.value === pluginId)
}
