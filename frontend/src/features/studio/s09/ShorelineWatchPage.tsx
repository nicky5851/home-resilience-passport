"use client"

import { useEffect, useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { Shoreline } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StatTile } from "@/features/studio/components/StatTile"
import { StudioNav } from "@/features/studio/components/StudioNav"

const SCENARIO_LABEL: Record<string, string> = {
  with_smp: "With shoreline management",
  no_active_intervention: "No active intervention",
}

export function ShorelineWatchPage({ homeRef }: { homeRef: string }) {
  const [result, setResult] = useState<Shoreline | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/shoreline", { params: { path: { ref: homeRef } } })
      .then((res) => setResult(unwrap(res)))
      .catch(setError)
  }, [homeRef])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Shoreline Watch</h1>
      <p>How far the coastline is projected to retreat near your home.</p>

      {error ? <ErrorState error={error} /> : null}
      {!result && !error ? <p className="s-mono">Checking coastal erosion projections…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          {!result.coastal ? (
            <div className="s-card">
              <p className="s-display text-xl">
                You&apos;re {((result.nearest_coast_m ?? 0) / 1000).toFixed(0)} km from the coast.
                Coastal erosion isn&apos;t a factor for your home.
              </p>
            </div>
          ) : (
            <>
              <div className="s-card">
                <p className="s-display text-xl">
                  {result.smp_policy
                    ? `Shoreline policy: ${result.smp_policy}`
                    : "Coastal erosion projections for your home"}
                </p>
                <p className="mt-2">{result.insurance_note}</p>
              </div>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {result.projections.map((p, i) => (
                  <StatTile
                    key={i}
                    eyebrow={`${p.epoch} - ${SCENARIO_LABEL[p.scenario]}`}
                    value={
                      p.home_inside_zone ? "Inside projected zone" : `${p.distance_m ?? "—"} m away`
                    }
                    unit={p.climate}
                  />
                ))}
              </div>

              <div>
                <p className="s-eyebrow mb-2">What to do</p>
                <div className="flex flex-col gap-2">
                  {result.advice_links.map((link) => (
                    <a key={link.url} href={link.url} className="s-focus-ring underline">
                      {link.label}
                    </a>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
