"use client"

import { useEffect, useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { GreenValue } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { StudioNav } from "@/features/studio/components/StudioNav"

const BANDS = ["A", "B", "C", "D", "E", "F", "G"]

function gbp(n: number): string {
  return `£${n.toLocaleString("en-GB")}`
}

export function GreenValueLensPage({ homeRef }: { homeRef: string }) {
  const [targetBand, setTargetBand] = useState("B")
  const [result, setResult] = useState<GreenValue | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    setResult(null)
    studioApi
      .GET("/api/v1/studio/homes/{ref}/green-value", {
        params: { path: { ref: homeRef }, query: { target_band: targetBand } },
      })
      .then(unwrap)
      .then(setResult)
      .catch(setError)
  }, [homeRef, targetBand])

  const maxPrice = result
    ? Math.max(result.range_high_gbp, ...result.comps.map((c) => c.indexed_gbp), 1)
    : 1

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Green Value Lens</h1>
      <p>What homes like yours sell for, and whether EPC upgrades could add value.</p>

      {error ? <ErrorState error={error} /> : null}

      <label className="s-card flex items-center gap-2">
        <span>Target EPC band</span>
        <select
          className="s-focus-ring rounded border px-2 py-1"
          value={targetBand}
          onChange={(e) => setTargetBand(e.target.value)}
        >
          {BANDS.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </label>

      {!result && !error ? <p className="s-mono">Looking up comparable sales…</p> : null}

      {result && (
        <div className="space-y-4">
          <div className="s-card">
            <p className="s-eyebrow">
              {result.method === "comparables"
                ? `${result.comparables_count} comparable sales`
                : "Local authority average (too few comparable sales nearby)"}
            </p>
            <p className="s-display text-xl">{gbp(result.indexed_median_gbp)}</p>
            <p className="s-mono text-sm">
              Range {gbp(result.range_low_gbp)} – {gbp(result.range_high_gbp)}
            </p>
          </div>

          {result.comps.length > 0 ? (
            <div className="s-card">
              <p className="s-eyebrow mb-2">Comparable sales (indexed to today)</p>
              <div className="space-y-1">
                {result.comps.map((c, i) => (
                  <div key={`${c.month}-${i}`} className="flex items-center gap-2">
                    <span className="s-mono w-20 shrink-0 text-sm">{c.month}</span>
                    <div
                      className="h-4 rounded"
                      style={{
                        width: `${Math.max(2, (c.indexed_gbp / maxPrice) * 100)}%`,
                        background: "var(--s-green-700)",
                      }}
                    />
                    <span className="s-mono shrink-0 text-sm">{gbp(c.indexed_gbp)}</span>
                    <span className="s-mono shrink-0 text-xs opacity-60">
                      {Math.round(c.distance_m)}m
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="s-card">
            <p className="s-eyebrow">
              Upgrading from {result.current_band ?? "unknown"} to {result.target_band}
            </p>
            {result.uplift_low_gbp != null && result.uplift_high_gbp != null ? (
              <p className="s-display text-xl">
                +{gbp(result.uplift_low_gbp)} – {gbp(result.uplift_high_gbp)}
              </p>
            ) : (
              <p className="s-mono">No current EPC band on record.</p>
            )}
            {result.plan_cost_low_gbp != null && result.plan_cost_high_gbp != null ? (
              <p className="s-mono text-sm">
                Plan cost: {gbp(result.plan_cost_low_gbp)} – {gbp(result.plan_cost_high_gbp)}
              </p>
            ) : null}
          </div>

          <div>
            <p className="s-eyebrow mb-2">Sources</p>
            <ul className="s-mono space-y-1 text-sm">
              {result.premium_sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} className="s-focus-ring underline">
                    {s.study} ({s.year})
                  </a>{" "}
                  — {s.pct_low}–{s.pct_high}% per EPC band step
                </li>
              ))}
            </ul>
          </div>

          <p className="s-mono text-sm opacity-70">{result.disclaimer}</p>
          {result.fallback_used ? (
            <p className="s-mono text-sm opacity-70">
              Live sales data was unreachable; showing a local authority average instead.
            </p>
          ) : null}
        </div>
      )}
    </div>
  )
}
