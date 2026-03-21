import type {
  StrategyPluginFieldDefinition,
  StrategyPluginMetadata,
} from '@/entities/strategy/types'

export const DEFAULT_PLUGIN_VERSION = '1.0.0'

export function getPluginOption(pluginOptions: readonly StrategyPluginMetadata[], pluginId: string) {
  return pluginOptions.find((option) => option.plugin_id === pluginId)
}

export function getPluginSummaryFields(pluginOptions: readonly StrategyPluginMetadata[], pluginId: string) {
  return getPluginOption(pluginOptions, pluginId)?.fields.filter((field) => field.summary) ?? []
}

export function formatPluginConfigValue(field: StrategyPluginFieldDefinition, value: unknown): string {
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
