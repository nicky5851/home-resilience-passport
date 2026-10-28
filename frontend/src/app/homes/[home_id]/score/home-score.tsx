"use client"

import Link from "next/link"

import { RequireUser } from "@/components/auth/require-user"
import { ScoreDashboard } from "@/components/journey/score-dashboard"
import { usePassport } from "@/lib/journey/use-passport"

export function HomeScore({ homeId }: { homeId: string }) {
  return <RequireUser>{() => <ScoreBody homeId={homeId} />}</RequireUser>
}

function ScoreBody({ homeId }: { homeId: string }) {
  const state = usePassport(homeId)

  if (state.status === "loading") return <p className="text-muted-foreground">Loading…</p>
  if (state.status === "error") return <p role="alert">{state.error.detail}</p>

  const { passport } = state
  return (
    <div className="space-y-6">
      <ScoreDashboard score={passport.latest_score} property={passport.property} />
      <Link
        href={`/homes/${homeId}/plan`}
        className="text-deep inline-block text-sm underline underline-offset-4"
      >
        See your improvement plan →
      </Link>
    </div>
  )
}
