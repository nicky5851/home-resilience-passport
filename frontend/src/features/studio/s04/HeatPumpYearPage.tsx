"use client"

import { useEffect, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { HeatPumpYear } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

const FLOW_TEMPS = [35, 45, 55] as const
const MONTH_LABEL = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
]

export function HeatPumpYearPage({ homeRef }: { homeRef: string }) {
  const [flowTemp, setFlowTemp] = useState<(typeof FLOW_TEMPS)[number]>(45)
  const [result, setResult] = useState<HeatPumpYear | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    studioApi
      .POST("/api/v1/studio/homes/{ref}/heat-pump-year", {
        params: { path: { ref: homeRef } },
        body: { flow_temp_c: flowTemp, keep_gas_standing_charge: false },
      })
      .then((res) => {
        if (!cancelled) setResult(unwrap(res))
      })
      .catch((e) => {
        if (!cancelled) setError(e)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [homeRef, flowTemp])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Heat Pump Year</h1>
      <p>A full year of a heat pump at this home, simulated hour by hour on real weather.</p>

      {error ? <ErrorState error={error} /> : null}
      {loading && !result ? <p className="s-mono">Simulating a year of weather…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          <div className="s-card">
            <p className="s-eyebrow">A {result.recommended_kw} kW heat pump would cost</p>
            <p className="s-display text-4xl">
              £{result.annual.hp_cost_gbp.toLocaleString()}{" "}
              <span className="text-base">a year</span>
            </p>
            <p className="mt-1">
              {result.annual.saving_gbp >= 0
                ? `About £${result.annual.saving_gbp.toLocaleString()} less than gas a year.`
                : `About £${Math.abs(result.annual.saving_gbp).toLocaleString()} more than gas a year.`}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatTile eyebrow="SCOP (seasonal efficiency)" value={result.scop.toFixed(2)} />
            <StatTile
              eyebrow="Coldest hour coped"
              value={result.coldest_hour.coped ? "Yes" : "No"}
              unit={`at ${result.coldest_hour.temp_c}°C`}
            />
            <StatTile
              eyebrow="Net cost after grant"
              value={`£${result.net_cost_low_gbp.toLocaleString()}–£${result.net_cost_high_gbp.toLocaleString()}`}
            />
          </div>

          <div className="s-card flex flex-wrap items-center gap-2">
            <span className="s-mono">Flow temperature</span>
            {FLOW_TEMPS.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setFlowTemp(t)}
                className="s-focus-ring rounded-full border px-3 py-1"
                style={{
                  borderColor: "var(--s-stone-200)",
                  background: flowTemp === t ? "var(--s-green-700)" : "transparent",
                  color: flowTemp === t ? "white" : "inherit",
                }}
              >
                {t}°C
              </button>
            ))}
            <span className="s-mono">
              Lower flow temperature = bigger radiators, higher efficiency
            </span>
          </div>

          <div className="s-card" style={{ height: 280 }}>
            <p className="s-eyebrow">Monthly cost: heat pump vs gas</p>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={result.monthly.map((m) => ({ ...m, label: MONTH_LABEL[m.month - 1] }))}
                margin={{ top: 20, right: 10, bottom: 10, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" />
                <YAxis unit="£" />
                <Tooltip />
                <Bar dataKey="hp_cost_gbp" name="Heat pump" fill="var(--s-green-500)" />
                <Bar dataKey="gas_cost_gbp" name="Gas" fill="var(--s-stone-500)" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="s-card" style={{ height: 240 }}>
            <p className="s-eyebrow">Daily mean COP across the year</p>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={result.daily} margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
                <XAxis dataKey="date" tick={false} />
                <YAxis domain={[1, 5]} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="cop_mean"
                  stroke="var(--s-green-700)"
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <p className="s-mono">
            On {result.coldest_hour.at.slice(0, 10)} it was {result.coldest_hour.temp_c}°C. Your{" "}
            {result.recommended_kw} kW heat pump would{" "}
            {result.coldest_hour.coped ? "have coped" : "not have coped"}.
          </p>
        </div>
      )}
    </div>
  )
}
