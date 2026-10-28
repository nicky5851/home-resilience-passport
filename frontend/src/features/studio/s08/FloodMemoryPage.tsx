"use client"

import { useEffect, useState } from "react"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { FloodMemory } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

export function FloodMemoryPage({ homeRef }: { homeRef: string }) {
  const [result, setResult] = useState<FloodMemory | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/flood-memory", { params: { path: { ref: homeRef } } })
      .then((res) => setResult(unwrap(res)))
      .catch(setError)
  }, [homeRef])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Flood Memory</h1>
      <p>Every recorded flood near your home since 1946, decade by decade.</p>

      {error ? <ErrorState error={error} /> : null}
      {!result && !error ? <p className="s-mono">Reading recorded flood outlines…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          <div className="s-card">
            <p className="s-display text-xl">
              {result.nearest_m != null
                ? result.inside_any_outline
                  ? "Your home sits inside a recorded flood outline."
                  : `The nearest recorded flood was ${result.nearest_m} m away.`
                : "No recorded floods were found nearby."}
            </p>
            <p className="mt-2">{result.caveat}</p>
          </div>

          {result.by_decade.length > 0 && (
            <div className="s-card" style={{ height: 220 }}>
              <p className="s-eyebrow">Recorded floods by decade</p>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={result.by_decade}
                  margin={{ top: 20, right: 10, bottom: 10, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="decade" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#1F5F8B" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {result.events.length > 0 && (
            <div>
              <p className="s-eyebrow mb-2">Recorded events</p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                {result.events.map((e, i) => (
                  <div key={i} className="s-card">
                    <p className="s-display text-lg">{e.name ?? "Unnamed flood event"}</p>
                    <p>
                      {e.start_date ?? "Date unknown"} - {e.distance_m} m away
                      {e.contains_home ? " (inside the outline)" : ""}
                    </p>
                    {e.source ? <p className="s-mono">Source: {e.source}</p> : null}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <StatTile
              eyebrow="Inside a recorded outline"
              value={result.inside_any_outline ? "Yes" : "No"}
            />
            <StatTile
              eyebrow="Nearest recorded flood"
              value={result.nearest_m != null ? `${result.nearest_m} m` : "None found"}
            />
          </div>
        </div>
      )}
    </div>
  )
}
