"use client"

import { useEffect, useState } from "react"

import { RequireUser } from "@/components/auth/require-user"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { HomeSummary } from "@/lib/api/types"

function HomesList() {
  const [homes, setHomes] = useState<HomeSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .GET("/api/v1/homes")
      .then(unwrap)
      .then(setHomes)
      .catch((e: unknown) => setError(isApiError(e) ? e.detail : "Could not load your homes."))
  }, [])

  if (error) return <p role="alert">{error}</p>
  if (!homes) return <p className="text-muted-foreground">Loading…</p>
  if (homes.length === 0) return <p>You have not added a home yet.</p>
  return (
    <ul className="space-y-2">
      {homes.map((h) => (
        <li key={h.home_id} className="border-border rounded-md border p-3">
          {h.line1}, {h.postcode}
          {h.score && ` · Score ${h.score.value} (${h.score.band})`}
        </li>
      ))}
    </ul>
  )
}

// Protected page placeholder: L13 builds the full "My homes" list.
export function MyHomes() {
  return (
    <RequireUser>
      {(user) => (
        <>
          <p className="text-muted-foreground">Logged in as {user.email}</p>
          <HomesList />
        </>
      )}
    </RequireUser>
  )
}
