"use client"

import { useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { NetZeroRoad, NetZeroRoadStep } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { StudioNav } from "@/features/studio/components/StudioNav"

const AVAILABLE_MEASURES = [
  { id: "loft-insulation", label: "Loft insulation top-up" },
  { id: "led-lighting", label: "LED lighting throughout" },
]

export function NetZeroRoadPage({ homeRef }: { homeRef: string }) {
  const [enabled, setEnabled] = useState<Record<string, boolean>>({})
  const [years, setYears] = useState<Record<string, number>>({})
  const [result, setResult] = useState<NetZeroRoad | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    const steps: NetZeroRoadStep[] = AVAILABLE_MEASURES.filter((m) => enabled[m.id]).map((m) => ({
      measure_id: m.id,
      year: years[m.id] ?? 2030,
    }))
    studioApi
      .POST("/api/v1/studio/homes/{ref}/net-zero-road", {
        params: { path: { ref: homeRef } },
        body: { steps },
      })
      .then(unwrap)
      .then((r) => {
        setResult(r)
        if (Object.keys(years).length === 0 && r.default_steps.length > 0) {
          const nextYears: Record<string, number> = {}
          const nextEnabled: Record<string, boolean> = {}
          for (const s of r.default_steps) {
            nextYears[s.measure_id] = s.year
            nextEnabled[s.measure_id] = true
          }
          setYears(nextYears)
          setEnabled(nextEnabled)
        }
      })
      .catch(setError)
  }, [homeRef, enabled, years])

  const chartData =
    result?.years.map((y) => ({
      year: y.year,
      do_nothing: y.co2_kg_do_nothing,
      with_plan: y.co2_kg_with_plan,
      pathway: y.pathway_kg,
    })) ?? []

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Net Zero Road</h1>
      <p>The home&apos;s carbon from 2025 to 2050, and how your plan bends the curve.</p>

      {error ? <ErrorState error={error} /> : null}

      <div className="s-card space-y-2">
        <p className="s-eyebrow">Place your upgrades</p>
        {AVAILABLE_MEASURES.map((m) => (
          <div key={m.id} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={Boolean(enabled[m.id])}
              onChange={(e) => setEnabled({ ...enabled, [m.id]: e.target.checked })}
            />
            <span className="flex-1">{m.label}</span>
            <label className="s-mono flex items-center gap-1 text-sm">
              Year
              <input
                type="number"
                min={2025}
                max={2050}
                className="s-focus-ring w-20 rounded border px-1"
                value={years[m.id] ?? 2030}
                onChange={(e) => setYears({ ...years, [m.id]: Number(e.target.value) })}
                disabled={!enabled[m.id]}
              />
            </label>
          </div>
        ))}
      </div>

      {!result && !error ? <p className="s-mono">Charting the road ahead…</p> : null}

      {result && (
        <div className="space-y-4">
          <div className="s-card">
            <p className="s-eyebrow">Milestone</p>
            <p className="s-display text-xl">
              {result.near_zero_year
                ? `Near zero by ${result.near_zero_year}.`
                : "Not yet on track for near zero by 2050."}
            </p>
            <p className="s-mono">
              {(result.cumulative_saved_kg / 1000).toFixed(1)} tonnes saved by 2050.
            </p>
          </div>

          <div className="s-card h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 20, right: 10, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis unit="kg" width={60} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="do_nothing"
                  name="Do nothing"
                  stroke="var(--s-stone-500)"
                  fill="var(--s-stone-500)"
                  fillOpacity={0.15}
                />
                <Area
                  type="monotone"
                  dataKey="with_plan"
                  name="With plan"
                  stroke="var(--s-green-500)"
                  fill="var(--s-green-500)"
                  fillOpacity={0.25}
                />
                <Line
                  type="monotone"
                  dataKey="pathway"
                  name="CCC pathway"
                  stroke="var(--s-brass-500, #b08d57)"
                  strokeDasharray="4 4"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
