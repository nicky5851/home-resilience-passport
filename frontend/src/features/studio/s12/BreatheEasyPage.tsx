"use client"

import { useEffect, useRef, useState } from "react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { BreatheEasy, BreatheEasyRequest } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StudioNav } from "@/features/studio/components/StudioNav"

const DEFAULTS: BreatheEasyRequest = { pollen_sensitive: false, pollution_sensitive: false }

function formatHour(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString("en-GB", { weekday: "short", hour: "2-digit" })
}

export function BreatheEasyPage({ homeRef }: { homeRef: string }) {
  const [sensitivity, setSensitivity] = useState<BreatheEasyRequest>(DEFAULTS)
  const [result, setResult] = useState<BreatheEasy | null>(null)
  const [error, setError] = useState<unknown>(null)
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  function load(body: BreatheEasyRequest) {
    studioApi
      .POST("/api/v1/studio/homes/{ref}/breathe-easy", { params: { path: { ref: homeRef } }, body })
      .then(unwrap)
      .then(setResult)
      .catch(setError)
  }

  useEffect(() => {
    load(DEFAULTS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [homeRef])

  function update(patch: Partial<BreatheEasyRequest>) {
    const next = { ...sensitivity, ...patch }
    setSensitivity(next)
    if (debounce.current) clearTimeout(debounce.current)
    debounce.current = setTimeout(() => load(next), 150)
  }

  const chartData = result?.hours.map((h) => ({ at: formatHour(h.at), score: h.score })) ?? []

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Breathe Easy</h1>
      <p>When to open the windows for fresh air, without letting in pollution or pollen.</p>

      {error ? <ErrorState error={error} /> : null}

      <div className="s-card flex flex-wrap gap-6">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={sensitivity.pollen_sensitive}
            onChange={(e) => update({ pollen_sensitive: e.target.checked })}
          />
          <span>I&apos;m sensitive to pollen</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={sensitivity.pollution_sensitive}
            onChange={(e) => update({ pollution_sensitive: e.target.checked })}
          />
          <span>I&apos;m sensitive to air pollution</span>
        </label>
        <p className="s-mono w-full">Only used to tune advice right now, never saved.</p>
      </div>

      {!result && !error ? <p className="s-mono">Reading the next 72 hours…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          <div className="s-card">
            <p className="s-display text-xl">{result.today_summary}</p>
          </div>

          <div className="s-card" style={{ height: 240 }}>
            <p className="s-eyebrow">Airing score, next 72 hours</p>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 20, right: 10, bottom: 10, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="at" interval={11} />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Area type="monotone" dataKey="score" stroke="#2E7D53" fill="#C8E6D4" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="s-eyebrow mb-2">Best windows to air the house</p>
              <div className="flex flex-col gap-2">
                {result.best_windows.length === 0 ? (
                  <p>No clear best window today.</p>
                ) : (
                  result.best_windows.map((w, i) => (
                    <div key={i} className="s-card">
                      <p>
                        {formatHour(w.start_at)} – {formatHour(w.end_at)}
                      </p>
                      <p className="s-mono">{w.reason}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div>
              <p className="s-eyebrow mb-2">Keep windows shut</p>
              <div className="flex flex-col gap-2">
                {result.avoid_windows.length === 0 ? (
                  <p>No windows to avoid today.</p>
                ) : (
                  result.avoid_windows.map((w, i) => (
                    <div key={i} className="s-card">
                      <p>
                        {formatHour(w.start_at)} – {formatHour(w.end_at)}
                      </p>
                      <p className="s-mono">{w.reason}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
