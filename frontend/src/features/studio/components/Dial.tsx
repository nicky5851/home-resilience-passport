"use client"

import { NumberTicker } from "@/features/studio/components/NumberTicker"

const BAND_COLOR: Record<string, string> = {
  A: "var(--s-epc-a)",
  B: "var(--s-epc-b)",
  C: "var(--s-epc-c)",
  D: "var(--s-epc-d)",
  E: "var(--s-epc-e)",
  F: "var(--s-epc-f)",
  G: "var(--s-epc-g)",
}

/** A 0-100 ring gauge with the value and band in the middle (docs/studio/N_20_function.md §2.4). */
export function Dial({ value, band, size = 160 }: { value: number; band: string; size?: number }) {
  const r = size / 2 - 10
  const c = 2 * Math.PI * r
  const offset = c * (1 - value / 100)
  const color = BAND_COLOR[band] ?? "var(--s-green-500)"

  return (
    <div style={{ width: size, height: size, position: "relative" }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--s-stone-200)"
          strokeWidth={10}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 640ms var(--s-ease-out)" }}
        />
      </svg>
      <div
        className="s-display"
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ fontSize: size * 0.28 }}>
          <NumberTicker value={value} />
        </div>
        <div className="s-mono" style={{ color }}>
          Band {band}
        </div>
      </div>
    </div>
  )
}
