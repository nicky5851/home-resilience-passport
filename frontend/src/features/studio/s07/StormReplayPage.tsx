"use client"

import { useEffect, useState } from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { EventSummary, Replay, StormReplayIndex } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StudioNav } from "@/features/studio/components/StudioNav"

const KIND_UNIT: Record<string, string> = { wind: "km/h", rain: "mm", heat: "°C" }

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function StormReplayPage({ homeRef }: { homeRef: string }) {
  const [index, setIndex] = useState<StormReplayIndex | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [replay, setReplay] = useState<Replay | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/storm-replay", { params: { path: { ref: homeRef } } })
      .then((res) => {
        const body = unwrap(res)
        setIndex(body)
        setSelected(body.hardest_event_id)
      })
      .catch(setError)
  }, [homeRef])

  useEffect(() => {
    if (!selected) return
    setReplay(null)
    studioApi
      .GET("/api/v1/studio/homes/{ref}/storm-replay/{event_id}", {
        params: { path: { ref: homeRef, event_id: selected } },
      })
      .then((res) => setReplay(unwrap(res)))
      .catch(setError)
  }, [homeRef, selected])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Storm Replay</h1>
      <p>Real storms and heatwaves, replayed hour by hour at your exact location.</p>

      {error ? <ErrorState error={error} /> : null}
      {!index ? <p className="s-mono">Loading events…</p> : null}

      {index && (
        <div className="space-y-6">
          {index.fallback_used ? <FallbackChip /> : null}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {index.events.map((e: EventSummary) => (
              <button
                key={e.id}
                type="button"
                onClick={() => setSelected(e.id)}
                className="s-card s-focus-ring text-left"
                style={{
                  borderColor: e.id === selected ? "var(--s-green-700)" : undefined,
                  outline: e.id === selected ? "2px solid var(--s-green-700)" : undefined,
                }}
              >
                <p className="s-display text-lg">
                  {e.name}
                  {e.id === index.hardest_event_id ? (
                    <span className="s-mono ml-2" style={{ color: "#A86200" }}>
                      Hit you hardest
                    </span>
                  ) : null}
                </p>
                <p>{e.headline}</p>
                <div
                  className="mt-2 h-2 rounded-full"
                  style={{ background: "var(--s-stone-200)" }}
                >
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${Math.round(e.severity * 100)}%`,
                      background: "var(--s-green-700)",
                    }}
                  />
                </div>
              </button>
            ))}
          </div>

          {replay && (
            <div className="space-y-4">
              {replay.fallback_used ? <FallbackChip /> : null}
              <div className="s-card" style={{ height: 280 }}>
                <p className="s-eyebrow">
                  {replay.event.name} - {KIND_UNIT[replay.event.kind]}
                </p>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={replay.hourly}
                    margin={{ top: 20, right: 10, bottom: 10, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="at" tickFormatter={(v) => timeLabel(v)} interval={Math.max(0, Math.floor(replay.hourly.length / 6))} />
                    <YAxis />
                    <Tooltip labelFormatter={(v) => (typeof v === "string" ? timeLabel(v) : "")} />
                    {replay.event.kind === "wind" && (
                      <Line type="monotone" dataKey="gust_kmh" stroke="var(--s-green-700)" dot={false} isAnimationActive={false} name="Gust (km/h)" />
                    )}
                    {replay.event.kind === "rain" && (
                      <Line type="monotone" dataKey="rain_mm" stroke="#1F5F8B" dot={false} isAnimationActive={false} name="Rain (mm)" />
                    )}
                    {replay.event.kind === "heat" && (
                      <>
                        <Line type="monotone" dataKey="temp_c" stroke="var(--s-stone-500)" dot={false} isAnimationActive={false} name="Outside" />
                        <Line type="monotone" dataKey="indoor_now_c" stroke="#A86200" dot={false} isAnimationActive={false} name="Inside now" />
                        <Line type="monotone" dataKey="indoor_with_measures_c" stroke="var(--s-green-700)" dot={false} isAnimationActive={false} name="Inside with measures" />
                      </>
                    )}
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div>
                <p className="s-eyebrow mb-2">What would have helped</p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {replay.lessons.map((l, i) => (
                    <div key={i} className="s-card">
                      <p>{l.text}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
