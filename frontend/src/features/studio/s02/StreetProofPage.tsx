"use client"

import { useEffect, useState } from "react"
import {
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { StreetProof } from "@/features/studio/api/types"
import { EmptyState } from "@/features/studio/components/EmptyState"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { Reveal } from "@/features/studio/components/Reveal"
import { SkeletonBlock } from "@/features/studio/components/SkeletonBlock"
import { StudioNav } from "@/features/studio/components/StudioNav"

const EPC_COLOR: Record<string, string> = {
  A: "var(--s-epc-a)",
  B: "var(--s-epc-b)",
  C: "var(--s-epc-c)",
  D: "var(--s-epc-d)",
  E: "var(--s-epc-e)",
  F: "var(--s-epc-f)",
  G: "var(--s-epc-g)",
}

export function StreetProofPage({ homeRef }: { homeRef: string }) {
  const [data, setData] = useState<StreetProof | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/street-proof", { params: { path: { ref: homeRef } } })
      .then(unwrap)
      .then(setData)
      .catch(setError)
  }, [homeRef])

  if (error) return <ErrorState error={error} />
  if (!data) return <SkeletonBlock height={400} />

  const scatter = data.band_distribution.flatMap((b) =>
    Array.from({ length: b.count }, (_, i) => ({ x: i, band: b.band })),
  )

  return (
    <div className="space-y-8">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Street Proof</h1>
      {data.fallback_used && <FallbackChip />}

      <p className="s-display text-xl">
        {data.peers_count} homes like yours within range.{" "}
        {data.improvers_count > 0 &&
          `${data.improvers_count} have improved their EPC${
            data.median_sap_gain ? `, typically by ${data.median_sap_gain} SAP points` : ""
          }.`}
      </p>
      <p className="s-mono">{data.peer_definition}</p>
      {data.partial && <p className="s-mono">Still gathering some nearby certificates.</p>}

      {data.peers_count === 0 ? (
        <EmptyState
          title="Not enough nearby certificates yet"
          body="We couldn't find peer homes nearby, or the EPC register didn't answer in time."
        />
      ) : (
        <>
          <div className="s-card" style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 10, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" dataKey="x" hide domain={[-1, Math.max(10, scatter.length)]} />
                <YAxis type="number" dataKey={() => 0} hide domain={[-1, 1]} />
                <Tooltip formatter={(_v, _n, p) => (p?.payload as { band: string })?.band} />
                <Scatter data={scatter} fill="var(--s-green-500)">
                  {scatter.map((d, i) => (
                    <Cell key={i} fill={EPC_COLOR[d.band] ?? "var(--s-stone-500)"} />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {data.top_upgrades.length > 0 && (
            <div className="space-y-3">
              <h2 className="s-display text-lg">What improvers did</h2>
              {data.top_upgrades.map((u) => (
                <div key={u.label}>
                  <div className="flex justify-between text-sm">
                    <span>{u.label}</span>
                    <span>
                      {u.share_pct}% of improvers
                      {u.median_sap_gain ? ` · +${u.median_sap_gain} SAP` : ""}
                    </span>
                  </div>
                  <div
                    className="h-2 overflow-hidden rounded-full"
                    style={{ background: "var(--s-stone-200)" }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${u.share_pct}%`, background: "var(--s-brass)" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {data.stories.length > 0 && (
            <div className="space-y-3">
              <h2 className="s-display text-lg">Nearby stories</h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {data.stories.map((s, i) => (
                  <Reveal index={i} key={i}>
                    <div className="s-card">
                      <p className="s-display text-lg">
                        {s.from_band} → {s.to_band}
                      </p>
                      <p className="s-mono">
                        about {s.distance_m} m away · {s.year_from} → {s.year_to}
                      </p>
                      <ul className="mt-2 flex flex-wrap gap-1">
                        {s.upgrades.map((u) => (
                          <li
                            key={u}
                            className="rounded-full px-2 py-0.5 text-xs"
                            style={{
                              background: "var(--s-green-100)",
                              color: "var(--s-green-700)",
                            }}
                          >
                            {u}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </Reveal>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
