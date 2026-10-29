"use client"

import { useEffect, useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { Affordability } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { StudioNav } from "@/features/studio/components/StudioNav"

const PLAN_MEASURE_IDS = "loft-insulation,led-lighting"

function gbp(n: number): string {
  return `£${n.toLocaleString("en-GB")}`
}

export function AffordabilityStressTestPage({ homeRef }: { homeRef: string }) {
  const [withPlan, setWithPlan] = useState(false)
  const [result, setResult] = useState<Affordability | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/affordability", {
        params: {
          path: { ref: homeRef },
          query: withPlan ? { measure_ids: PLAN_MEASURE_IDS } : {},
        },
      })
      .then(unwrap)
      .then(setResult)
      .catch(setError)
  }, [homeRef, withPlan])

  const maxCost = result ? Math.max(...result.scenarios.map((s) => s.annual_cost_gbp)) : 1

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Affordability Stress Test</h1>
      <p>How exposed your energy bill is to price shocks, and how much your plan protects it.</p>

      {error ? <ErrorState error={error} /> : null}

      <label className="s-card flex items-center gap-2">
        <input type="checkbox" checked={withPlan} onChange={(e) => setWithPlan(e.target.checked)} />
        <span>With my plan</span>
      </label>

      {!result && !error ? <p className="s-mono">Running the stress test…</p> : null}

      {result && (
        <div className="space-y-4">
          {result.scenarios.map((s) => {
            const shown =
              withPlan && s.annual_cost_after_gbp != null
                ? s.annual_cost_after_gbp
                : s.annual_cost_gbp
            const widthPct = Math.max(2, (shown / maxCost) * 100)
            const thresholdPct =
              s.pct_income != null
                ? Math.min(100, (s.annual_cost_gbp / maxCost) * (10 / s.pct_income))
                : null
            return (
              <div key={s.id} className="s-card">
                <p className="s-eyebrow">{s.label}</p>
                <div
                  className="relative mt-2 h-8 rounded"
                  style={{ background: "var(--s-stone-100)" }}
                >
                  <div
                    className="h-8 rounded"
                    style={{ width: `${widthPct}%`, background: "var(--s-green-700)" }}
                  />
                  {thresholdPct != null ? (
                    <div
                      className="absolute top-0 h-8 border-l-2 border-dashed"
                      style={{
                        left: `${thresholdPct}%`,
                        borderColor: "var(--s-brass-500, #b08d57)",
                      }}
                      title="10% of household income"
                    />
                  ) : null}
                </div>
                <p className="s-display mt-1 text-xl">
                  {gbp(shown)}
                  {s.pct_income != null ? (
                    <span className="s-mono ml-2 text-sm">
                      ({withPlan && s.pct_income_after != null ? s.pct_income_after : s.pct_income}%
                      of income)
                    </span>
                  ) : null}
                </p>
                {(withPlan ? s.above_10pct_after : s.above_10pct) ? (
                  <p className="s-mono">Above 10% of income: help may be available.</p>
                ) : null}
              </div>
            )
          })}

          <div>
            <p className="s-eyebrow mb-2">Help if you need it</p>
            <div className="flex flex-col gap-1">
              {result.help_links.map((link) => (
                <a key={link.url} href={link.url} className="s-focus-ring underline">
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
