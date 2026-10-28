"use client"

import { useEffect, useRef, useState } from "react"

import { tickerValue } from "@/features/studio/lib/ticker"

/** Counts to `value` over 640ms with tabular numerals (docs/studio/N_20_function.md §2.4).
 * `prefers-reduced-motion: reduce` renders the final value instantly. */
export function NumberTicker({
  value,
  format = (v: number) => String(Math.round(v)),
}: {
  value: number
  format?: (v: number) => string
}) {
  const [display, setDisplay] = useState(value)
  const fromRef = useRef(value)

  useEffect(() => {
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (reduceMotion) {
      setDisplay(value)
      fromRef.current = value
      return
    }
    const from = fromRef.current
    const to = value
    const start = performance.now()
    const duration = 640
    let frame: number
    const tick = () => {
      const elapsed = performance.now() - start
      setDisplay(tickerValue(from, to, elapsed, duration))
      if (elapsed < duration) frame = requestAnimationFrame(tick)
      else fromRef.current = to
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value])

  return (
    <span aria-live="polite" style={{ fontVariantNumeric: "tabular-nums" }}>
      {format(display)}
    </span>
  )
}
