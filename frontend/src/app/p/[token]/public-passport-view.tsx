"use client"

import { useEffect, useState } from "react"

import { EventsTimeline } from "@/components/journey/events-timeline"
import { RiskView } from "@/components/journey/risk-view"
import { ScoreDashboard } from "@/components/journey/score-dashboard"
import { api, unwrap } from "@/lib/api/client"
import { ApiError } from "@/lib/api/errors"
import type { PublicPassport } from "@/lib/api/types"

type State =
  | { status: "loading"; passport: null; error: null }
  | { status: "ready"; passport: PublicPassport; error: null }
  | { status: "inactive"; passport: null; error: null }
  | { status: "error"; passport: null; error: ApiError }

/** Read-only public passport (CONTRACT §3, §6): no household, no email, no certificates. */
export function PublicPassportView({ token }: { token: string }) {
  const [state, setState] = useState<State>({ status: "loading", passport: null, error: null })

  useEffect(() => {
    api
      .GET("/api/v1/public/passport/{share_token}", { params: { path: { share_token: token } } })
      .then(unwrap)
      .then((passport) => setState({ status: "ready", passport, error: null }))
      .catch((e: unknown) => {
        const err = e instanceof ApiError ? e : ApiError.from(0, null)
        setState(
          err.status === 404
            ? { status: "inactive", passport: null, error: null }
            : { status: "error", passport: null, error: err },
        )
      })
  }, [token])

  if (state.status === "loading") return <p className="text-muted-foreground">Loading…</p>
  if (state.status === "inactive") return <p role="alert">This link is no longer active.</p>
  if (state.status === "error") return <p role="alert">{state.error.detail}</p>

  const { passport } = state
  return (
    <div className="space-y-8">
      <h1 className="text-deep text-2xl font-semibold">{passport.address.line1}</h1>
      <RiskView risk={passport.latest_risk} address={passport.address} />
      <ScoreDashboard score={passport.latest_score} property={passport.property} />
      <div className="space-y-2">
        <h2 className="font-semibold">Timeline</h2>
        <EventsTimeline events={passport.events} />
      </div>
    </div>
  )
}
