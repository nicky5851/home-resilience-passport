"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { isApiError } from "@/lib/api/errors"
import type { DemoHome } from "@/lib/api/types"
import { loginPath, useUser } from "@/lib/auth/use-user"
import { createAndAssessHome } from "@/lib/journey/create-home"

/** "Make this my home" (CONTRACT §4.1): needs login, then copies the demo's data onto a real home. */
export function MakeMyHomeButton({ home }: { home: DemoHome }) {
  const router = useRouter()
  const user = useUser()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onClick() {
    if (user.status !== "authenticated") {
      router.push(loginPath(`/demo/${home.slug}`))
      return
    }
    setBusy(true)
    setError(null)
    try {
      const homeId = await createAndAssessHome(home.address, home.household, home.property)
      router.push(`/homes/${homeId}/risk`)
    } catch (e) {
      setError(isApiError(e) ? e.detail : "Something went wrong. Please try again.")
      setBusy(false)
    }
  }

  return (
    <div className="space-y-1">
      <Button type="button" onClick={onClick} disabled={busy}>
        {busy ? "Setting up your home…" : "Make this my home"}
      </Button>
      {error && (
        <p role="alert" className="text-risk text-sm">
          {error}
        </p>
      )}
    </div>
  )
}
