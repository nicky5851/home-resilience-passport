"use client"

import Link from "next/link"

import { RequireUser } from "@/components/auth/require-user"
import { RiskView } from "@/components/journey/risk-view"
import { usePassport } from "@/lib/journey/use-passport"

export function HomeRisk({ homeId }: { homeId: string }) {
  return <RequireUser>{() => <RiskBody homeId={homeId} />}</RequireUser>
}

function RiskBody({ homeId }: { homeId: string }) {
  const state = usePassport(homeId)

  if (state.status === "loading") return <p className="text-muted-foreground">Loading…</p>
  if (state.status === "error") return <p role="alert">{state.error.detail}</p>

  const { passport } = state
  return (
    <div className="space-y-6">
      <RiskView risk={passport.latest_risk} address={passport.address} />
      <Link
        href={`/homes/${homeId}/score`}
        className="text-deep inline-block text-sm underline underline-offset-4"
      >
        See your Resilience Score →
      </Link>
    </div>
  )
}
