"use client"

import { useEffect, useState } from "react"

import { RequireUser } from "@/components/auth/require-user"
import { EventsTimeline } from "@/components/journey/events-timeline"
import { ScoreHistory } from "@/components/journey/score-history"
import { api, unwrap } from "@/lib/api/client"
import type { Measure, Passport } from "@/lib/api/types"
import { usePassport } from "@/lib/journey/use-passport"

import { RecordWorkForm } from "./record-work-form"
import { ShareControls } from "./share-controls"

export function HomePassportPage({ homeId }: { homeId: string }) {
  return <RequireUser>{() => <PassportBody homeId={homeId} />}</RequireUser>
}

function PassportBody({ homeId }: { homeId: string }) {
  const state = usePassport(homeId)
  const [passport, setPassport] = useState<Passport | null>(null)
  const [measures, setMeasures] = useState<Measure[]>([])

  useEffect(() => {
    if (state.status === "ready") setPassport(state.passport)
  }, [state])

  useEffect(() => {
    if (state.status !== "ready") return
    const plan = state.passport.plan
    if (plan) {
      setMeasures(plan.items.map((i) => i.measure))
      return
    }
    api
      .POST("/api/v1/homes/{home_id}/plan", { params: { path: { home_id: homeId } }, body: {} })
      .then(unwrap)
      .then((p) => setMeasures(p.items.map((i) => i.measure)))
      .catch(() => setMeasures([]))
  }, [state, homeId])

  async function refresh() {
    const p = unwrap(
      await api.GET("/api/v1/homes/{home_id}/passport", { params: { path: { home_id: homeId } } }),
    )
    setPassport(p)
  }

  if (state.status === "loading" || !passport)
    return <p className="text-muted-foreground">Loading…</p>
  if (state.status === "error") return <p role="alert">{state.error.detail}</p>

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-lg font-semibold">{passport.address.line1}</h2>
        <p className="text-muted-foreground text-sm">
          Score {passport.latest_score.value} ({passport.latest_score.band})
        </p>
      </div>

      <div className="space-y-2">
        <h2 className="font-semibold">Score history</h2>
        <ScoreHistory events={passport.events} />
      </div>

      <div className="space-y-2">
        <h2 className="font-semibold">Timeline</h2>
        <EventsTimeline events={passport.events} />
      </div>

      <div className="space-y-2">
        <h2 className="font-semibold">Record completed work</h2>
        <RecordWorkForm homeId={homeId} measures={measures} onRecorded={refresh} />
      </div>

      <div className="space-y-2">
        <h2 className="font-semibold">Share this passport</h2>
        <p className="text-muted-foreground text-sm">
          Anyone with the link can see your risks, score and plan — never your household answers.
        </p>
        <ShareControls
          homeId={homeId}
          shareToken={passport.share_token}
          onChange={(token) => setPassport({ ...passport, share_token: token })}
        />
      </div>
    </div>
  )
}
