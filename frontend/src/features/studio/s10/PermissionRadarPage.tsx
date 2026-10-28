"use client"

import { useEffect, useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { PermissionRadar } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StudioNav } from "@/features/studio/components/StudioNav"

const VERDICT_STYLE: Record<string, { label: string; className: string }> = {
  likely_permitted: { label: "Likely fine", className: "bg-emerald-100 text-emerald-900" },
  check_council: { label: "Check with council", className: "bg-amber-100 text-amber-900" },
  consent_needed: { label: "Consent needed", className: "bg-rose-100 text-rose-900" },
  not_applicable: { label: "Not applicable", className: "bg-slate-100 text-slate-700" },
}

export function PermissionRadarPage({ homeRef }: { homeRef: string }) {
  const [result, setResult] = useState<PermissionRadar | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/permission-radar", { params: { path: { ref: homeRef } } })
      .then((res) => setResult(unwrap(res)))
      .catch(setError)
  }, [homeRef])

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Permission Radar</h1>
      <p>Which upgrades in your plan need planning permission, before you get quotes.</p>

      {error ? <ErrorState error={error} /> : null}
      {!result && !error ? <p className="s-mono">Scanning planning constraints…</p> : null}

      {result && (
        <div className="space-y-6">
          {result.fallback_used ? <FallbackChip /> : null}

          {result.local_planning_authority ? (
            <p className="s-eyebrow">Local planning authority: {result.local_planning_authority}</p>
          ) : null}

          <div>
            <p className="s-eyebrow mb-2">Constraints found near your home</p>
            <div className="flex flex-wrap gap-2">
              {result.constraints.map((c) => (
                <span
                  key={c.dataset}
                  className={
                    "s-mono rounded-full px-3 py-1 text-sm " +
                    (c.applies === true
                      ? "bg-amber-100 text-amber-900"
                      : c.applies === false
                        ? "bg-slate-100 text-slate-500"
                        : "bg-slate-200 text-slate-400")
                  }
                >
                  {c.label}
                  {c.applies === true
                    ? ` — ${c.name ?? "applies"}`
                    : c.applies === null
                      ? " (unknown)"
                      : ""}
                </span>
              ))}
            </div>
          </div>

          <div>
            <p className="s-eyebrow mb-2">Your plan</p>
            <div className="flex flex-col gap-2">
              {result.measures.map((m) => {
                const style = VERDICT_STYLE[m.verdict]
                const isOpen = expanded === m.measure_id
                return (
                  <div key={m.measure_id} className="s-card">
                    <button
                      type="button"
                      className="s-focus-ring flex w-full items-center justify-between gap-4 text-left"
                      onClick={() => setExpanded(isOpen ? null : m.measure_id)}
                    >
                      <span className="s-display">{m.name}</span>
                      <span
                        className={"rounded-full px-3 py-1 text-sm font-medium " + style.className}
                      >
                        {style.label}
                      </span>
                    </button>
                    {isOpen && (
                      <div className="mt-3 space-y-1">
                        {m.reasons.map((reason, i) => (
                          <p key={i}>{reason}</p>
                        ))}
                        <a href={m.guidance_url} className="s-focus-ring underline">
                          Official guidance
                        </a>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          <p className="s-mono">{result.disclaimer}</p>
        </div>
      )}
    </div>
  )
}
