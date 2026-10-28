"use client"

import Link from "next/link"
import { useEffect, useMemo, useRef, useState } from "react"

import { api, unwrap as unwrapMain } from "@/lib/api/client"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type {
  HotspotId,
  SandboxInit,
  SandboxMeasure,
  SandboxState,
} from "@/features/studio/api/types"
import { Dial } from "@/features/studio/components/Dial"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { SkeletonBlock } from "@/features/studio/components/SkeletonBlock"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"
import { formatGbp } from "@/features/studio/lib/format"
import { HouseDiagram } from "@/features/studio/s01/HouseDiagram"

export function SandboxPage({ homeRef }: { homeRef: string }) {
  const [init, setInit] = useState<SandboxInit | null>(null)
  const [state, setState] = useState<SandboxState | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<unknown>(null)
  const debounce = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/sandbox", { params: { path: { ref: homeRef } } })
      .then(unwrap)
      .then((data) => {
        setInit(data)
        setState(data.baseline)
        setSelected(new Set(data.measures.filter((m) => m.already_done).map((m) => m.measure.id)))
      })
      .catch(setError)
  }, [homeRef])

  const byHotspot = useMemo(() => {
    const groups = new Map<HotspotId, SandboxMeasure[]>()
    for (const m of init?.measures ?? []) {
      const list = groups.get(m.hotspot) ?? []
      list.push(m)
      groups.set(m.hotspot, list)
    }
    return groups
  }, [init])

  const activeHotspots = useMemo(() => {
    const ids = new Set<HotspotId>()
    for (const m of init?.measures ?? []) if (selected.has(m.measure.id)) ids.add(m.hotspot)
    return ids
  }, [init, selected])

  function toggle(measureId: string) {
    setSaved(false)
    const next = new Set(selected)
    if (next.has(measureId)) next.delete(measureId)
    else next.add(measureId)
    setSelected(next)

    if (debounce.current) clearTimeout(debounce.current)
    debounce.current = setTimeout(() => {
      studioApi
        .POST("/api/v1/studio/homes/{ref}/sandbox/simulate", {
          params: { path: { ref: homeRef } },
          body: { measure_ids: Array.from(next) },
        })
        .then(unwrap)
        .then(setState)
        .catch(setError)
    }, 150)
  }

  function reset() {
    setSaved(false)
    setSelected(new Set(init?.measures.filter((m) => m.already_done).map((m) => m.measure.id)))
    setState(init?.baseline ?? null)
  }

  async function saveAsPlan() {
    try {
      unwrapMain(
        await api.POST("/api/v1/homes/{home_id}/plan", {
          params: { path: { home_id: homeRef } },
          body: { selected_ids: Array.from(selected) },
        }),
      )
      setSaved(true)
    } catch (e) {
      setError(e)
    }
  }

  if (error) return <ErrorState error={error} />
  if (!init || !state) return <SkeletonBlock height={400} />

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Retrofit Sandbox</h1>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="s-card lg:col-span-7">
          <HouseDiagram active={activeHotspots} />
        </div>

        <div className="space-y-4 lg:col-span-5">
          <div className="s-card flex items-center justify-center">
            <Dial value={state.score.value} band={state.score.band} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <StatTile
              eyebrow="Cost"
              value={`${formatGbp(state.cost_low_gbp)}-${formatGbp(state.cost_high_gbp)}`}
            />
            <StatTile eyebrow="Saving / yr" value={formatGbp(state.bill_saving_gbp_per_year)} />
            <StatTile eyebrow="CO₂ saved / yr" value={`${state.co2_saved_kg_per_year}`} unit="kg" />
          </div>
          {state.payback_years != null && (
            <p className="s-mono">Pays back in about {state.payback_years} years.</p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {state.components.map((c) => (
          <div key={c.name}>
            <div className="flex justify-between text-sm">
              <span className="capitalize">{c.name}</span>
              <span>
                {c.before.toFixed(1)} → {c.after.toFixed(1)} / {c.max_points}
              </span>
            </div>
            <div
              className="h-2 overflow-hidden rounded-full"
              style={{ background: "var(--s-stone-200)" }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${(c.after / c.max_points) * 100}%`,
                  background: "var(--s-green-500)",
                  transition: "width 640ms var(--s-ease-out)",
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="s-card space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="s-display text-lg">Measures</h2>
          <div className="flex gap-2">
            <button type="button" className="s-focus-ring s-mono underline" onClick={reset}>
              Reset
            </button>
            {init.home.ref.startsWith("demo-") ? (
              <Link href="/login" className="s-focus-ring s-mono underline">
                Sign in to save
              </Link>
            ) : (
              <button type="button" className="s-focus-ring s-mono underline" onClick={saveAsPlan}>
                {saved ? "Saved ✓" : "Save as my plan"}
              </button>
            )}
          </div>
        </div>
        {Array.from(byHotspot.entries()).map(([hotspot, measures]) => (
          <div key={hotspot}>
            <p className="s-eyebrow">
              {init.hotspots.find((h) => h.id === hotspot)?.label ?? hotspot}
            </p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {measures.map((m) => {
                const isOn = selected.has(m.measure.id)
                return (
                  <li key={m.measure.id}>
                    <button
                      type="button"
                      onClick={() => toggle(m.measure.id)}
                      className="s-focus-ring rounded-full border px-3 py-1 text-sm"
                      style={{
                        borderColor: isOn ? "var(--s-green-700)" : "var(--s-stone-200)",
                        background: isOn ? "var(--s-green-100)" : "transparent",
                      }}
                      aria-pressed={isOn}
                    >
                      {m.measure.name}
                      {m.measure.needs_landlord ? " (landlord)" : ""}
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}
