"use client"

import { useRef, useState } from "react"
import {
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { ApiError } from "@/lib/api/errors"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { Fingerprint } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

const RATING_LABEL: Record<string, string> = {
  excellent: "Excellent",
  good: "Good",
  average: "Average",
  poor: "Poor",
}

export function MeterFingerprintPage({ homeRef }: { homeRef: string }) {
  const [fuel, setFuel] = useState<"gas" | "electric_heat_pump" | "electric_direct">("gas")
  const [unit, setUnit] = useState<"kwh" | "m3">("kwh")
  const [result, setResult] = useState<Fingerprint | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  async function upload(file: File) {
    setBusy(true)
    setError(null)
    try {
      const form = new FormData()
      form.append("file", file)
      form.append("fuel", fuel)
      form.append("unit", unit)
      const res = await fetch(`/api/v1/studio/homes/${homeRef}/meter-fingerprint`, {
        method: "POST",
        body: form,
      })
      if (!res.ok) throw ApiError.from(res.status, await res.json().catch(() => ({})))
      setResult(await res.json())
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  async function trySample() {
    setBusy(true)
    setError(null)
    try {
      setResult(
        unwrap(
          await studioApi.GET("/api/v1/studio/homes/{ref}/meter-fingerprint/sample", {
            params: { path: { ref: homeRef }, query: { fuel } },
          }),
        ),
      )
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Meter Fingerprint</h1>
      <p>Download your supplier&apos;s usage export and upload it here, or try sample data.</p>

      <div className="s-card flex flex-wrap items-center gap-3">
        <select
          value={fuel}
          onChange={(e) => setFuel(e.target.value as typeof fuel)}
          className="s-focus-ring rounded border px-2 py-1"
        >
          <option value="gas">Gas boiler</option>
          <option value="electric_heat_pump">Electric heat pump</option>
          <option value="electric_direct">Direct electric</option>
        </select>
        <select
          value={unit}
          onChange={(e) => setUnit(e.target.value as typeof unit)}
          className="s-focus-ring rounded border px-2 py-1"
        >
          <option value="kwh">kWh</option>
          <option value="m3">m³</option>
        </select>
        <input
          ref={fileInput}
          type="file"
          accept=".csv"
          className="s-focus-ring"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void upload(file)
          }}
        />
        <button
          type="button"
          onClick={trySample}
          disabled={busy}
          className="s-focus-ring s-mono underline"
        >
          Try with sample data
        </button>
        <a
          href={`/api/v1/studio/homes/${homeRef}/meter-fingerprint/sample.csv`}
          className="s-focus-ring s-mono underline"
        >
          Download sample CSV
        </a>
      </div>
      <p className="s-mono">
        We read your file once to measure your home and then delete it. Demo uploads are never
        stored.
      </p>

      {error ? <ErrorState error={error} /> : null}

      {result && (
        <div className="space-y-6">
          <div className="s-card">
            <p className="s-eyebrow">Heat-loss coefficient</p>
            <p className="s-display text-4xl">
              {result.htc_w_per_k} <span className="text-base">W/K</span>
            </p>
            <p className="s-mono">
              95% range {result.htc_ci_low}–{result.htc_ci_high} W/K
            </p>
            <p className="mt-2">
              Your home loses about {result.htc_w_per_k} watts for every degree colder it gets
              outside — like a {(result.htc_w_per_k / 1000).toFixed(1)} kW heater running whenever
              it&apos;s 1° colder.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatTile eyebrow="Rating" value={RATING_LABEL[result.rating] ?? result.rating} />
            <StatTile
              eyebrow="Heat-loss parameter"
              value={result.hlp_w_per_m2k != null ? result.hlp_w_per_m2k.toFixed(2) : "—"}
              unit="W/m²K"
            />
            <StatTile eyebrow="Fit quality (R²)" value={result.r2.toFixed(2)} />
          </div>

          <div className="s-card" style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="t_mean_c" name="Mean outside temp (°C)" unit="°C" />
                <YAxis type="number" dataKey="kwh" name="kWh/day" unit=" kWh" />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                <Scatter data={result.scatter} fill="var(--s-stone-500)" name="Daily readings" />
                <Line
                  data={result.fit}
                  dataKey="kwh"
                  stroke="var(--s-green-500)"
                  dot={false}
                  strokeWidth={2}
                  name="Fit"
                  isAnimationActive={false}
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
