import { Box } from '@mui/material'
import { useDeferredValue, useEffect, useMemo, useRef } from 'react'

interface AnimatedOdometerProps {
  value: number
  precision?: number
  suffix?: string
  theme?: string
  duration?: number
  showPositiveSign?: boolean
}

function buildFormat(precision: number): string {
  if (precision <= 0) {
    return '(,ddd)'
  }
  return `(,ddd).${'d'.repeat(precision)}`
}

function buildFallback(value: number, precision: number): string {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
  })
}

export function AnimatedOdometer({
  value,
  precision = 0,
  suffix,
  theme = 'minimal',
  duration = 700,
  showPositiveSign = false,
}: AnimatedOdometerProps) {
  const valueRef = useRef<HTMLSpanElement | null>(null)
  const instanceRef = useRef<import('odometer').default | null>(null)
  const normalizedValue = useMemo(() => Number(value.toFixed(precision)), [precision, value])
  const deferredValue = useDeferredValue(normalizedValue)
  const format = useMemo(() => buildFormat(precision), [precision])
  const fallback = useMemo(() => buildFallback(normalizedValue, precision), [normalizedValue, precision])

  useEffect(() => {
    let isDisposed = false

    async function mountOdometer() {
      const odometerModule = await import('odometer')
      const Odometer = odometerModule.default
      if (isDisposed || valueRef.current === null) {
        return
      }

      valueRef.current.textContent = fallback
      instanceRef.current = new Odometer({
        el: valueRef.current,
        value: normalizedValue,
        format,
        theme,
        duration,
      })
      instanceRef.current.render()
    }

    void mountOdometer()

    return () => {
      isDisposed = true
      instanceRef.current = null
    }
  }, [duration, fallback, format, normalizedValue, theme])

  useEffect(() => {
    if (instanceRef.current !== null) {
      instanceRef.current.update(deferredValue)
      return
    }
    if (valueRef.current !== null) {
      valueRef.current.textContent = buildFallback(deferredValue, precision)
    }
  }, [deferredValue, precision])

  return (
    <Box component="span" className="animated-odometer">
      {showPositiveSign && normalizedValue > 0 ? (
        <Box component="span" className="animated-odometer__sign">
          +
        </Box>
      ) : null}
      <Box component="span" ref={valueRef} className="animated-odometer__value">
        {fallback}
      </Box>
      {suffix ? (
        <Box component="span" className="animated-odometer__suffix">
          {suffix}
        </Box>
      ) : null}
    </Box>
  )
}
