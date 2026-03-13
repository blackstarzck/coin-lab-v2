import { useCallback, useLayoutEffect, useMemo, useRef } from 'react'

const ENTER_TRANSITION = 'transform 320ms cubic-bezier(0.16, 1, 0.3, 1), opacity 320ms ease'

export function useAnimatedTableRows(rowIds: string[]) {
  const rowElementsRef = useRef(new Map<string, HTMLTableRowElement>())
  const previousTopByIdRef = useRef(new Map<string, number>())
  const rafHandlesRef = useRef<number[]>([])
  const animationKey = useMemo(() => rowIds.join('|'), [rowIds])

  const setRowRef = useCallback(
    (rowId: string) => (element: HTMLTableRowElement | null) => {
      if (element === null) {
        rowElementsRef.current.delete(rowId)
        return
      }
      rowElementsRef.current.set(rowId, element)
    },
    [],
  )

  useLayoutEffect(() => {
    for (const handle of rafHandlesRef.current) {
      window.cancelAnimationFrame(handle)
    }
    rafHandlesRef.current = []

    const nextTopById = new Map<string, number>()
    for (const rowId of rowIds) {
      const element = rowElementsRef.current.get(rowId)
      if (element === undefined) {
        continue
      }
      nextTopById.set(rowId, element.getBoundingClientRect().top)
    }

    if (previousTopByIdRef.current.size === 0) {
      previousTopByIdRef.current = nextTopById
      return undefined
    }

    for (const rowId of rowIds) {
      const element = rowElementsRef.current.get(rowId)
      const nextTop = nextTopById.get(rowId)
      if (element === undefined || nextTop === undefined) {
        continue
      }

      element.style.willChange = 'transform, opacity'
      const previousTop = previousTopByIdRef.current.get(rowId)
      if (previousTop === undefined) {
        element.style.transition = 'none'
        element.style.opacity = '0'
        element.style.transform = 'translateY(-18px)'
        const handle = window.requestAnimationFrame(() => {
          element.style.transition = ENTER_TRANSITION
          element.style.opacity = '1'
          element.style.transform = 'translateY(0)'
        })
        rafHandlesRef.current.push(handle)
        continue
      }

      const delta = previousTop - nextTop
      if (Math.abs(delta) < 1) {
        element.style.transition = ''
        element.style.transform = ''
        element.style.opacity = ''
        continue
      }

      element.style.transition = 'none'
      element.style.transform = `translateY(${delta}px)`
      const handle = window.requestAnimationFrame(() => {
        element.style.transition = ENTER_TRANSITION
        element.style.transform = 'translateY(0)'
      })
      rafHandlesRef.current.push(handle)
    }

    previousTopByIdRef.current = nextTopById

    return () => {
      for (const handle of rafHandlesRef.current) {
        window.cancelAnimationFrame(handle)
      }
      rafHandlesRef.current = []
    }
  }, [animationKey])

  return { setRowRef }
}
