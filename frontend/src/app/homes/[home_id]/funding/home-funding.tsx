"use client"

import { useEffect, useState } from "react"

import { RequireUser } from "@/components/auth/require-user"
import { FundingBundleView } from "@/components/journey/funding-bundle"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { FundingBundle } from "@/lib/api/types"

export function HomeFunding({ homeId }: { homeId: string }) {
  return <RequireUser>{() => <FundingBody homeId={homeId} />}</RequireUser>
}

function FundingBody({ homeId }: { homeId: string }) {
  const [bundle, setBundle] = useState<FundingBundle | null>(null)
  const [cost, setCost] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        // The current plan's selection (default selection on a first visit) drives the bundle.
        const plan = unwrap(
          await api.POST("/api/v1/homes/{home_id}/plan", {
            params: { path: { home_id: homeId } },
            body: {},
          }),
        )
        const selectedIds = plan.items.filter((i) => i.selected).map((i) => i.measure.id)
        const funding = unwrap(
          await api.POST("/api/v1/homes/{home_id}/funding", {
            params: { path: { home_id: homeId } },
            body: { selected_ids: selectedIds },
          }),
        )
        if (!cancelled) {
          setBundle(funding)
          setCost(plan.total_cost_low_gbp)
        }
      } catch (e) {
        if (!cancelled) setError(isApiError(e) ? e.detail : "Could not load your funding.")
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [homeId])

  if (error) return <p role="alert">{error}</p>
  if (!bundle) return <p className="text-muted-foreground">Loading…</p>

  return <FundingBundleView bundle={bundle} cost={cost} />
}
