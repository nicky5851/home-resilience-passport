"use client"

import { useEffect, useRef, useState } from "react"

/** Fade + rise on scroll into view, staggered by `index` (docs/studio/N_20_function.md §2.4). */
export function Reveal({ children, index = 0 }: { children: React.ReactNode; index?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.1 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={visible ? "s-reveal" : ""}
      style={{
        animationDelay: visible ? `${index * 40}ms` : undefined,
        opacity: visible ? undefined : 0,
      }}
    >
      {children}
    </div>
  )
}
