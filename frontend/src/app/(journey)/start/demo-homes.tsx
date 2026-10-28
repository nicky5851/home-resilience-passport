"use client"

import Link from "next/link"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { DemoHome } from "@/lib/api/types"

const HAZARD_LABEL: Record<DemoHome["hazard_shown"], string> = {
  river_sea_flood: "River and sea flooding",
  overheating: "Overheating",
  storm: "Storm",
  subsidence: "Subsidence",
  low_risk: "Low risk, high score",
}

/** "Try a demo home": lists the 5 demo homes, each already fully assessed (CONTRACT §4.1). */
export function DemoHomesButton() {
  const [homes, setHomes] = useState<DemoHome[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setHomes(unwrap(await api.GET("/api/v1/demo/homes")))
    } catch (e) {
      setError(isApiError(e) ? e.detail : "Could not load the demo homes.")
    } finally {
      setLoading(false)
    }
  }

  if (!homes) {
    return (
      <Button type="button" variant="outline" onClick={load} disabled={loading}>
        {loading ? "Loading demo homes…" : "Try a demo home"}
      </Button>
    )
  }

  return (
    <ul className="space-y-2">
      {error && (
        <li role="alert" className="text-risk text-sm">
          {error}
        </li>
      )}
      {homes.map((home) => (
        <li key={home.slug}>
          <Link
            href={`/demo/${home.slug}`}
            className="border-border hover:bg-mint block rounded-md border p-3 transition-colors"
          >
            <span className="font-medium">{home.address.line1}</span>
            <span className="text-muted-foreground block text-sm">
              {HAZARD_LABEL[home.hazard_shown]} · Score {home.score.value} ({home.score.band})
            </span>
          </Link>
        </li>
      ))}
    </ul>
  )
}
