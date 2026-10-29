"use client"

import { useEffect, useRef, useState } from "react"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { DampLab, DampLabRequest } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

const SURFACE_LABEL: Record<string, string> = {
  wall: "Wall",
  corner: "Cold corner",
  window: "Window glass",
}

const DEFAULT_ANSWERS: DampLabRequest = {
  occupants: 2,
  dries_clothes_indoors: false,
  kitchen_extractor: true,
  bathroom_extractor: true,
  trickle_vents: true,
  heating_setpoint_c: 18,
}

export function DampMouldLabPage({ homeRef }: { homeRef: string }) {
  const [answers, setAnswers] = useState<DampLabRequest>(DEFAULT_ANSWERS)
  const [result, setResult] = useState<DampLab | null>(null)
  const [error, setError] = useState<unknown>(null)
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  function load(body: DampLabRequest) {
    studioApi
      .POST("/api/v1/studio/homes/{ref}/damp-lab", { params: { path: { ref: homeRef } }, body })
      .then(unwrap)
      .then(setResult)
      .catch(setError)
  }

  useEffect(() => {
    load(DEFAULT_ANSWERS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [homeRef])

  function update(patch: Partial<DampLabRequest>) {
    const next = { ...answers, ...patch }
    setAnswers(next)
    if (debounce.current) clearTimeout(debounce.current)
    debounce.current = setTimeout(() => load(next), 150)
  }

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Damp & Mould Lab</h1>
      <p>
        Damp is common and fixable. Most of it comes from moisture we make inside. Here&apos;s why
        your home gets damp, hour by hour on last winter&apos;s real weather.
      </p>

      {error ? <ErrorState error={error} /> : null}

      <div className="s-card space-y-3">
        <p className="s-eyebrow">Tell us about your home</p>
        <label className="flex items-center justify-between gap-4">
          <span>People living here</span>
          <input
            type="number"
            min={1}
            max={10}
            value={answers.occupants}
            onChange={(e) => update({ occupants: Number(e.target.value) })}
            className="s-focus-ring w-16 rounded border px-2 py-1"
          />
        </label>
        {(
          [
            ["dries_clothes_indoors", "Dry clothes indoors"],
            ["kitchen_extractor", "Kitchen extractor fan"],
            ["bathroom_extractor", "Bathroom extractor fan"],
            ["trickle_vents", "Trickle vents open"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center justify-between gap-4">
            <span>{label}</span>
            <input
              type="checkbox"
              checked={answers[key]}
              onChange={(e) => update({ [key]: e.target.checked } as Partial<DampLabRequest>)}
            />
          </label>
        ))}
        <label className="flex items-center justify-between gap-4">
          <span>Heating setpoint</span>
          <input
            type="number"
            step={0.5}
            value={answers.heating_setpoint_c}
            onChange={(e) => update({ heating_setpoint_c: Number(e.target.value) })}
            className="s-focus-ring w-20 rounded border px-2 py-1"
          />
        </label>
      </div>

      {!result && !error ? <p className="s-mono">Replaying last winter&apos;s weather…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          <p className="s-eyebrow">
            Winter {result.winter} · Wall U {result.wall_u} · Window U {result.window_u} · Moisture
            class {result.moisture_class}
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {result.surfaces.map((s) => (
              <div key={s.surface} className="relative">
                <StatTile
                  eyebrow={SURFACE_LABEL[s.surface]}
                  value={`${s.risk_hours_pct}%`}
                  unit="of hours at risk"
                  delta={s.level}
                />
              </div>
            ))}
          </div>

          {result.monthly.length > 0 && (
            <div className="s-card" style={{ height: 220 }}>
              <p className="s-eyebrow">Cold corner risk by month</p>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={result.monthly}
                  margin={{ top: 20, right: 10, bottom: 10, left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis unit="%" />
                  <Tooltip />
                  <Bar dataKey="corner_risk_pct" fill="#1F5F8B" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div>
            <p className="s-eyebrow mb-2">What would help most</p>
            <div className="flex flex-col gap-2">
              {result.interventions.map((i) => (
                <div key={i.id} className="s-card flex items-center justify-between gap-4">
                  <span>{i.label}</span>
                  <span className="s-mono">
                    {i.corner_risk_pct_after}% after
                    {i.delta_pct > 0 ? ` (-${i.delta_pct} pts)` : ""}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {result.landlord_note ? <p className="s-card">{result.landlord_note}</p> : null}
        </div>
      )}
    </div>
  )
}
