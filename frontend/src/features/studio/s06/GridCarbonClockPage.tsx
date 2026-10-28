"use client"

import { useEffect, useState } from "react"
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { GridCarbon } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

const REFRESH_MS = 15 * 60 * 1000

const MIX_COLOR: Record<string, string> = {
  wind: "var(--s-green-500)",
  solar: "#F4C430",
  nuclear: "var(--s-green-700)",
  gas: "var(--s-stone-500)",
  imports: "#9CA3AF",
  biomass: "#8B5E3C",
  hydro: "#1F5F8B",
  coal: "var(--s-forest-950)",
  other: "#D1D5DB",
}

const INDEX_COLOR: Record<string, string> = {
  "very low": "var(--s-green-500)",
  low: "var(--s-green-700)",
  moderate: "#A86200",
  high: "#C65D2E",
  "very high": "var(--s-forest-950)",
}

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
}

export function GridCarbonClockPage({ homeRef }: { homeRef: string }) {
  const [result, setResult] = useState<GridCarbon | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    let cancelled = false
    function load() {
      studioApi
        .GET("/api/v1/studio/homes/{ref}/grid-carbon", { params: { path: { ref: homeRef } } })
        .then((res) => {
          if (!cancelled) setResult(unwrap(res))
        })
        .catch((e) => {
          if (!cancelled) setError(e)
        })
    }
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [homeRef])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Grid Carbon Clock</h1>
      <p>See when your electricity is cleanest, and shift appliances there for free.</p>

      {error ? <ErrorState error={error} /> : null}
      {!result && !error ? <p className="s-mono">Reading the grid forecast…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div className="s-card">
              <p className="s-eyebrow">{result.region_name} right now</p>
              <p
                className="s-display text-4xl"
                style={{ color: INDEX_COLOR[result.now.index] ?? "inherit" }}
              >
                {result.now.intensity_g_per_kwh} <span className="text-base">gCO2/kWh</span>
              </p>
              <p className="mt-1 capitalize">{result.now.index}</p>
            </div>
            <div className="s-card" style={{ height: 200 }}>
              <p className="s-eyebrow">Generation mix</p>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={result.now.mix}
                    dataKey="percent"
                    nameKey="fuel"
                    innerRadius={40}
                    outerRadius={70}
                  >
                    {result.now.mix.map((m) => (
                      <Cell key={m.fuel} fill={MIX_COLOR[m.fuel] ?? "#D1D5DB"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="s-card" style={{ height: 240 }}>
            <p className="s-eyebrow">Next 48 hours</p>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={result.forecast}
                margin={{ top: 20, right: 10, bottom: 10, left: 0 }}
              >
                <XAxis
                  dataKey="from_at"
                  tickFormatter={timeLabel}
                  interval={Math.floor(result.forecast.length / 8)}
                />
                <YAxis unit=" g" />
                <Tooltip
                  labelFormatter={(label) => (typeof label === "string" ? timeLabel(label) : "")}
                />
                <Area
                  type="monotone"
                  dataKey="intensity_g_per_kwh"
                  stroke="var(--s-green-700)"
                  fill="var(--s-green-500)"
                  fillOpacity={0.3}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <StatTile
              eyebrow="Greenest slot"
              value={timeLabel(result.greenest_slot.from_at)}
              unit={`${result.greenest_slot.intensity_g_per_kwh} g`}
            />
            <StatTile
              eyebrow="Dirtiest slot"
              value={timeLabel(result.dirtiest_slot.from_at)}
              unit={`${result.dirtiest_slot.intensity_g_per_kwh} g`}
            />
          </div>

          <div>
            <p className="s-eyebrow mb-2">Best time for each appliance</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {result.best_windows.map((w) => (
                <div key={w.appliance_id} className="s-card">
                  <p className="s-display text-lg">{w.label}</p>
                  <p>
                    {timeLabel(w.start_at)}–{timeLabel(w.end_at)}
                  </p>
                  <p className="mt-1" style={{ color: "var(--s-green-700)" }}>
                    {w.saving_pct_vs_now > 0
                      ? `${w.saving_pct_vs_now}% less carbon than now`
                      : "No better than now"}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
