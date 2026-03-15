import type { CandlePoint } from '@/entities/market/types'

type JsonObject = Record<string, unknown>

export interface MovingAverageSetting {
  id: string
  type: 'ema' | 'sma'
  length: number
}

export interface ChartIndicatorSettings {
  movingAverages: MovingAverageSetting[]
  rsi: {
    length: number
  }
  macd: {
    fastLength: number
    slowLength: number
    signalLength: number
  }
}

export interface TimeValuePoint {
  time: string
  value: number
}

export interface HistogramPoint extends TimeValuePoint {
  color: string
}

export interface ChartIndicatorData {
  movingAverages: Record<string, TimeValuePoint[]>
  volume: HistogramPoint[]
  rsi: TimeValuePoint[]
  macd: {
    macdLine: TimeValuePoint[]
    signalLine: TimeValuePoint[]
    histogram: HistogramPoint[]
  }
}

const DEFAULT_MOVING_AVERAGES: MovingAverageSetting[] = [
  { id: 'ema-7', type: 'ema', length: 7 },
  { id: 'ema-21', type: 'ema', length: 21 },
]

const DEFAULT_RSI_LENGTH = 14
const DEFAULT_MACD_FAST_LENGTH = 12
const DEFAULT_MACD_SLOW_LENGTH = 26
const DEFAULT_MACD_SIGNAL_LENGTH = 9

function asObject(value: unknown): JsonObject {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as JsonObject)
    : {}
}

function asPositiveInteger(value: unknown): number | null {
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return null
  }
  return Math.round(parsed)
}

function addMovingAverage(
  map: Map<string, MovingAverageSetting>,
  type: 'ema' | 'sma',
  length: number | null,
): void {
  if (!length) {
    return
  }

  const id = `${type}-${length}`
  if (!map.has(id)) {
    map.set(id, { id, type, length })
  }
}

interface IndicatorAccumulator {
  movingAverages: Map<string, MovingAverageSetting>
  rsiLength: number | null
  macdFastLength: number | null
  macdSlowLength: number | null
  macdSignalLength: number | null
}

function collectIndicatorHints(value: unknown, accumulator: IndicatorAccumulator): void {
  if (Array.isArray(value)) {
    value.forEach((item) => collectIndicatorHints(item, accumulator))
    return
  }

  if (!value || typeof value !== 'object') {
    return
  }

  const node = value as JsonObject
  const indicatorName = typeof node.name === 'string' ? node.name.toLowerCase() : null
  const params = asObject(node.params)

  if (indicatorName === 'ema' || indicatorName === 'sma' || indicatorName === 'ma') {
    const length = asPositiveInteger(params.length ?? params.period ?? params.window ?? params.lookback)
    addMovingAverage(accumulator.movingAverages, indicatorName === 'sma' ? 'sma' : 'ema', length)
  }

  if (indicatorName === 'rsi') {
    accumulator.rsiLength = asPositiveInteger(params.length ?? params.period) ?? accumulator.rsiLength ?? DEFAULT_RSI_LENGTH
  }

  if (indicatorName === 'macd') {
    accumulator.macdFastLength = asPositiveInteger(params.fast ?? params.fast_length ?? params.short ?? params.short_length)
      ?? accumulator.macdFastLength
      ?? DEFAULT_MACD_FAST_LENGTH
    accumulator.macdSlowLength = asPositiveInteger(params.slow ?? params.slow_length ?? params.long ?? params.long_length)
      ?? accumulator.macdSlowLength
      ?? DEFAULT_MACD_SLOW_LENGTH
    accumulator.macdSignalLength = asPositiveInteger(params.signal ?? params.signal_length)
      ?? accumulator.macdSignalLength
      ?? DEFAULT_MACD_SIGNAL_LENGTH
  }

  Object.entries(node).forEach(([key, childValue]) => {
    const normalizedKey = key.toLowerCase()

    if (normalizedKey.startsWith('ema_')) {
      addMovingAverage(accumulator.movingAverages, 'ema', asPositiveInteger(childValue))
    }

    if (normalizedKey.startsWith('sma_')) {
      addMovingAverage(accumulator.movingAverages, 'sma', asPositiveInteger(childValue))
    }

    if (normalizedKey === 'rsi_length' || normalizedKey === 'rsi_period') {
      accumulator.rsiLength = asPositiveInteger(childValue) ?? accumulator.rsiLength
    }

    if (normalizedKey === 'macd_fast' || normalizedKey === 'macd_fast_length') {
      accumulator.macdFastLength = asPositiveInteger(childValue) ?? accumulator.macdFastLength
    }

    if (normalizedKey === 'macd_slow' || normalizedKey === 'macd_slow_length') {
      accumulator.macdSlowLength = asPositiveInteger(childValue) ?? accumulator.macdSlowLength
    }

    if (normalizedKey === 'macd_signal' || normalizedKey === 'macd_signal_length') {
      accumulator.macdSignalLength = asPositiveInteger(childValue) ?? accumulator.macdSignalLength
    }

    collectIndicatorHints(childValue, accumulator)
  })
}

export function resolveChartIndicatorSettings(config: Record<string, unknown> | null | undefined): ChartIndicatorSettings {
  const accumulator: IndicatorAccumulator = {
    movingAverages: new Map(),
    rsiLength: null,
    macdFastLength: null,
    macdSlowLength: null,
    macdSignalLength: null,
  }

  collectIndicatorHints(config ?? {}, accumulator)

  const movingAverages = Array.from(accumulator.movingAverages.values())
    .sort((left, right) => left.length - right.length)

  return {
    movingAverages: movingAverages.length > 0 ? movingAverages : DEFAULT_MOVING_AVERAGES,
    rsi: {
      length: accumulator.rsiLength ?? DEFAULT_RSI_LENGTH,
    },
    macd: {
      fastLength: accumulator.macdFastLength ?? DEFAULT_MACD_FAST_LENGTH,
      slowLength: accumulator.macdSlowLength ?? DEFAULT_MACD_SLOW_LENGTH,
      signalLength: accumulator.macdSignalLength ?? DEFAULT_MACD_SIGNAL_LENGTH,
    },
  }
}

function buildSma(candles: CandlePoint[], length: number): TimeValuePoint[] {
  const points: TimeValuePoint[] = []
  let rollingSum = 0

  for (let index = 0; index < candles.length; index += 1) {
    rollingSum += candles[index]!.close
    if (index >= length) {
      rollingSum -= candles[index - length]!.close
    }
    if (index >= length - 1) {
      points.push({
        time: candles[index]!.time,
        value: rollingSum / length,
      })
    }
  }

  return points
}

function buildEma(candles: CandlePoint[], length: number): TimeValuePoint[] {
  if (!candles.length) {
    return []
  }

  const alpha = 2 / (length + 1)
  const points: TimeValuePoint[] = []
  let previousValue = candles[0]!.close

  candles.forEach((candle, index) => {
    const nextValue = index === 0
      ? candle.close
      : (candle.close * alpha) + (previousValue * (1 - alpha))
    previousValue = nextValue
    points.push({
      time: candle.time,
      value: nextValue,
    })
  })

  return points
}

function buildRsi(candles: CandlePoint[], length: number): TimeValuePoint[] {
  if (candles.length <= length) {
    return []
  }

  let gainSum = 0
  let lossSum = 0

  for (let index = 1; index <= length; index += 1) {
    const change = candles[index]!.close - candles[index - 1]!.close
    gainSum += Math.max(change, 0)
    lossSum += Math.max(-change, 0)
  }

  let averageGain = gainSum / length
  let averageLoss = lossSum / length
  const points: TimeValuePoint[] = []

  const initialRsi = averageLoss === 0
    ? (averageGain === 0 ? 50 : 100)
    : 100 - (100 / (1 + (averageGain / averageLoss)))

  points.push({
    time: candles[length]!.time,
    value: initialRsi,
  })

  for (let index = length + 1; index < candles.length; index += 1) {
    const change = candles[index]!.close - candles[index - 1]!.close
    const gain = Math.max(change, 0)
    const loss = Math.max(-change, 0)

    averageGain = ((averageGain * (length - 1)) + gain) / length
    averageLoss = ((averageLoss * (length - 1)) + loss) / length

    const rsi = averageLoss === 0
      ? (averageGain === 0 ? 50 : 100)
      : 100 - (100 / (1 + (averageGain / averageLoss)))

    points.push({
      time: candles[index]!.time,
      value: rsi,
    })
  }

  return points
}

function buildMacd(candles: CandlePoint[], fastLength: number, slowLength: number, signalLength: number) {
  const fastEma = buildEma(candles, fastLength)
  const slowEma = buildEma(candles, slowLength)

  const macdValues = candles.map((candle, index) => ({
    time: candle.time,
    value: (fastEma[index]?.value ?? candle.close) - (slowEma[index]?.value ?? candle.close),
  }))

  if (!macdValues.length) {
    return {
      macdLine: [] as TimeValuePoint[],
      signalLine: [] as TimeValuePoint[],
      histogram: [] as HistogramPoint[],
    }
  }

  const signalValues: TimeValuePoint[] = []
  const alpha = 2 / (signalLength + 1)
  let previousSignal = macdValues[0]!.value

  macdValues.forEach((point, index) => {
    const nextSignal = index === 0
      ? point.value
      : (point.value * alpha) + (previousSignal * (1 - alpha))
    previousSignal = nextSignal
    signalValues.push({
      time: point.time,
      value: nextSignal,
    })
  })

  const histogram = macdValues.map((point, index) => {
    const diff = point.value - (signalValues[index]?.value ?? 0)
    return {
      time: point.time,
      value: diff,
      color: diff >= 0 ? 'rgba(22, 199, 132, 0.75)' : 'rgba(255, 91, 91, 0.75)',
    }
  })

  return {
    macdLine: macdValues,
    signalLine: signalValues,
    histogram,
  }
}

export function buildChartIndicatorData(candles: CandlePoint[], settings: ChartIndicatorSettings): ChartIndicatorData {
  const movingAverages = Object.fromEntries(
    settings.movingAverages.map((movingAverage) => [
      movingAverage.id,
      movingAverage.type === 'sma'
        ? buildSma(candles, movingAverage.length)
        : buildEma(candles, movingAverage.length),
    ]),
  )

  return {
    movingAverages,
    volume: candles.map((candle) => ({
      time: candle.time,
      value: candle.volume,
      color: candle.close >= candle.open ? 'rgba(239, 68, 68, 0.5)' : 'rgba(59, 130, 246, 0.5)',
    })),
    rsi: buildRsi(candles, settings.rsi.length),
    macd: buildMacd(
      candles,
      settings.macd.fastLength,
      settings.macd.slowLength,
      settings.macd.signalLength,
    ),
  }
}
