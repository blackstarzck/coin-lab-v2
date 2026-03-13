function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}

export function getStrategyUniverseMode(configJson: Record<string, unknown>): string | null {
  const universe = asRecord(configJson.universe)
  return typeof universe.mode === 'string' ? universe.mode : null
}

export function getStrategyStaticSymbols(configJson: Record<string, unknown>): string[] {
  if (getStrategyUniverseMode(configJson) !== 'static') {
    return []
  }

  const universe = asRecord(configJson.universe)
  if (!Array.isArray(universe.symbols)) {
    return []
  }

  const seen = new Set<string>()
  return universe.symbols
    .map((item) => String(item).trim().toUpperCase())
    .filter((symbol) => {
      if (!symbol || seen.has(symbol)) {
        return false
      }
      seen.add(symbol)
      return true
    })
}
