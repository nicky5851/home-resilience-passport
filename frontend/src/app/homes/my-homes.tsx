"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { RequireUser } from "@/components/auth/require-user"
import { Button } from "@/components/ui/button"
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

  async function deleteHome(homeId: string) {
    if (!homes) return
    try {
      unwrap(await api.DELETE("/api/v1/homes/{home_id}", { params: { path: { home_id: homeId } } }))
      setHomes(homes.filter((h) => h.home_id !== homeId))
    } catch (e) {
      setError(isApiError(e) ? e.detail : "Could not delete that home.")
    }
  }

  if (error) return <p role="alert">{error}</p>
  if (!homes) return <p className="text-muted-foreground">Loading…</p>
  if (homes.length === 0) return <p>You have not added a home yet.</p>
  return (
    <ul className="space-y-2">
      {homes.map((h) => (
        <li
          key={h.home_id}
          className="border-border flex flex-wrap items-center justify-between gap-2 rounded-md border p-3"
        >
          <Link href={`/homes/${h.home_id}/passport`} className="hover:underline">
            {h.line1}, {h.postcode}
            {h.score && ` · Score ${h.score.value} (${h.score.band})`}
          </Link>
          <Button type="button" variant="ghost" size="sm" onClick={() => deleteHome(h.home_id)}>
            Delete this home
          </Button>
        </li>
      ))}
    </ul>
  )
}

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
