import { useEffect, useMemo, useRef, useState, type RefObject } from 'react'

interface UseIncrementalTableRowsOptions<T> {
  items: T[]
  enabled: boolean
  pageSize: number
  resetKey: string
  rootRef: RefObject<HTMLElement | null>
}

export function useIncrementalTableRows<T>({
  items,
  enabled,
  pageSize,
  resetKey,
  rootRef,
}: UseIncrementalTableRowsOptions<T>) {
  const [state, setState] = useState({
    resetKey,
    visibleCount: pageSize,
  })
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const visibleCount = state.resetKey === resetKey ? state.visibleCount : pageSize

  useEffect(() => {
    if (!enabled || visibleCount >= items.length) {
      return
    }

    const root = rootRef.current
    const target = sentinelRef.current
    if (!root || !target) {
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries
        if (!entry?.isIntersecting) {
          return
        }

        setState((current) => {
          const currentVisibleCount = current.resetKey === resetKey ? current.visibleCount : pageSize
          return {
            resetKey,
            visibleCount: Math.min(currentVisibleCount + pageSize, items.length),
          }
        })
      },
      {
        root,
        rootMargin: '0px 0px 120px 0px',
        threshold: 0.1,
      },
    )

    observer.observe(target)
    return () => observer.disconnect()
  }, [enabled, items.length, pageSize, resetKey, rootRef, visibleCount])

  const visibleItems = useMemo(
    () => items.slice(0, visibleCount),
    [items, visibleCount],
  )

  return {
    visibleItems,
    visibleCount,
    totalCount: items.length,
    sentinelRef,
  }
}
