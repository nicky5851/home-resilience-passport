"use client"

import { useEffect, useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { WeekAhead } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StudioNav } from "@/features/studio/components/StudioNav"

const GLYPH_ICON: Record<string, string> = {
  sun: "☀️",
  cloud: "☁️",
  rain: "🌧️",
  heavy_rain: "🌧️🌧️",
  wind: "💨",
  frost: "❄️",
  snow: "🌨️",
  storm: "⛈️",
}

const LEVEL_COLOUR: Record<string, string> = {
  low: "var(--s-stone-500)",
  medium: "var(--s-brass-500, #b08d57)",
  high: "var(--s-red-600, #b3261e)",
}

function dayLabel(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { weekday: "short", day: "numeric" })
}

export function WeekAheadPage({ homeRef }: { homeRef: string }) {
  const [result, setResult] = useState<WeekAhead | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [done, setDone] = useState<Record<string, boolean>>({})

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/week-ahead", { params: { path: { ref: homeRef } } })
      .then(unwrap)
      .then(setResult)
      .catch(setError)
  }, [homeRef])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Week Ahead</h1>
      <p>This week&apos;s forecast, turned into simple jobs for your home.</p>

      {error ? <ErrorState error={error} /> : null}
      {!result && !error ? <p className="s-mono">Reading the week ahead…</p> : null}

      {result && (
        <div className="space-y-4">
          <div className="s-card flex items-center justify-between gap-2">
            <p className="s-display text-lg">{result.headline}</p>
            {result.fallback_used ? <FallbackChip /> : null}
          </div>

          <div className="flex gap-3 overflow-x-auto pb-2">
            {result.days.map((day) => (
              <div
                key={day.date}
                className="s-card w-56 shrink-0 space-y-2"
                style={{ scrollSnapAlign: "start" }}
              >
                <p className="s-eyebrow">{dayLabel(day.date)}</p>
                <p className="text-2xl" aria-hidden>
                  {GLYPH_ICON[day.glyph] ?? "☁️"}
                </p>
                <p className="s-mono text-sm">
                  {day.t_max_c != null ? `${Math.round(day.t_max_c)}°` : "–"} /{" "}
                  {day.t_min_c != null ? `${Math.round(day.t_min_c)}°` : "–"}
                </p>
                <p className="s-mono text-xs opacity-70">
                  {day.rain_mm != null ? `${day.rain_mm}mm rain` : "no rain data"} ·{" "}
                  {day.gust_kmh != null ? `${Math.round(day.gust_kmh)}km/h gusts` : "no wind data"}
                </p>

                {day.alerts.map((alert, i) => {
                  const key = `${day.date}-${i}`
                  return (
                    <div
                      key={key}
                      className="space-y-1 rounded border-l-2 pl-2"
                      style={{ borderColor: LEVEL_COLOUR[alert.level] }}
                    >
                      <p className="s-mono text-sm font-semibold">{alert.title}</p>
                      {alert.actions.map((action, j) => {
                        const actionKey = `${key}-${j}`
                        return (
                          <label key={actionKey} className="flex items-start gap-1 text-xs">
                            <input
                              type="checkbox"
                              checked={Boolean(done[actionKey])}
                              onChange={(e) => setDone({ ...done, [actionKey]: e.target.checked })}
                            />
                            <span>{action}</span>
                          </label>
                        )
                      })}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
