"use client"

import { useEffect, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { SolarResult } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

const BATTERIES = [0, 5, 10] as const
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

const SUITABILITY_LABEL: Record<string, string> = {
  good: "Good",
  fair: "Fair",
  poor: "Poor",
  freeholder_needed: "Needs freeholder permission",
}

function aspectLabel(deg: number): string {
  const names: Record<number, string> = {
    [-180]: "N",
    [-135]: "NE",
    [-90]: "E",
    [-45]: "SE",
    0: "S",
    45: "SW",
    90: "W",
    135: "NW",
  }
  return names[deg] ?? `${deg}°`
}

export function SolarRoofStudioPage({ homeRef }: { homeRef: string }) {
  const [aspect, setAspect] = useState(0)
  const [pitch, setPitch] = useState(35)
  const [battery, setBattery] = useState<(typeof BATTERIES)[number]>(0)
  const [result, setResult] = useState<SolarResult | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    studioApi
      .POST("/api/v1/studio/homes/{ref}/solar", {
        params: { path: { ref: homeRef } },
        body: { aspect_deg: aspect, pitch_deg: pitch, battery_kwh: battery },
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
  }, [homeRef, aspect, pitch, battery])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Solar Roof Studio</h1>
      <p>See whether solar panels make sense on your roof, and when they&apos;d pay back.</p>

      {error ? <ErrorState error={error} /> : null}
      {loading && !result ? <p className="s-mono">Checking your roof against PVGIS…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          {result.suitability === "freeholder_needed" ? (
            <div className="s-card">
              <p className="s-display text-xl">{result.suitability_note}</p>
            </div>
          ) : (
            <>
              <div className="s-card">
                <p className="s-eyebrow">
                  A {result.kwp} kWp system (
                  {result.kwp_source === "user" ? "your size" : "estimated from your roof"})
                </p>
                <p className="s-display text-4xl">
                  £{result.annual_saving_gbp.toLocaleString()}{" "}
                  <span className="text-base">a year</span>
                </p>
                <p className="mt-1">
                  {result.payback_years != null
                    ? `Pays back in about ${result.payback_years} years (around ${result.breakeven_year}).`
                    : "No saving at this orientation, so payback isn't meaningful."}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <StatTile
                  eyebrow="Annual generation"
                  value={result.annual_kwh.toLocaleString()}
                  unit="kWh"
                />
                <StatTile eyebrow="Suitability" value={SUITABILITY_LABEL[result.suitability]} />
                <StatTile
                  eyebrow="25-year saving"
                  value={`£${result.lifetime_saving_gbp.toLocaleString()}`}
                />
              </div>

              <div className="s-card flex flex-wrap items-center gap-4">
                <label className="flex flex-col gap-1">
                  <span className="s-mono">Aspect ({aspectLabel(aspect)})</span>
                  <input
                    type="range"
                    min={-180}
                    max={180}
                    step={45}
                    value={aspect}
                    onChange={(e) => setAspect(Number(e.target.value))}
                    className="s-focus-ring"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="s-mono">Pitch ({pitch}°)</span>
                  <input
                    type="range"
                    min={0}
                    max={60}
                    step={5}
                    value={pitch}
                    onChange={(e) => setPitch(Number(e.target.value))}
                    className="s-focus-ring"
                  />
                </label>
                <div className="flex flex-col gap-1">
                  <span className="s-mono">Battery</span>
                  <div className="flex gap-2">
                    {BATTERIES.map((b) => (
                      <button
                        key={b}
                        type="button"
                        onClick={() => setBattery(b)}
                        className="s-focus-ring rounded-full border px-3 py-1"
                        style={{
                          borderColor: "var(--s-stone-200)",
                          background: battery === b ? "var(--s-green-700)" : "transparent",
                          color: battery === b ? "white" : "inherit",
                        }}
                      >
                        {b === 0 ? "None" : `${b} kWh`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="s-card" style={{ height: 260 }}>
                <p className="s-eyebrow">Generation by roof direction</p>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart
                    data={result.orientation_rose.map((p) => ({
                      ...p,
                      direction: aspectLabel(p.aspect_deg),
                    }))}
                  >
                    <PolarGrid />
                    <PolarAngleAxis dataKey="direction" />
                    <Radar
                      dataKey="annual_kwh"
                      stroke="var(--s-green-500)"
                      fill="var(--s-green-500)"
                      fillOpacity={0.4}
                    />
                    <Tooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              <div className="s-card" style={{ height: 260 }}>
                <p className="s-eyebrow">Monthly generation</p>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={result.monthly_kwh.map((kwh, i) => ({ kwh, label: MONTH_LABEL[i] }))}
                    margin={{ top: 20, right: 10, bottom: 10, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" />
                    <YAxis unit=" kWh" />
                    <Tooltip />
                    <Bar dataKey="kwh" fill="var(--s-green-500)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
