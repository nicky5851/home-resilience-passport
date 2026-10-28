"use client"

import { FundingBundleView } from "@/components/journey/funding-bundle"
import { RiskView } from "@/components/journey/risk-view"
import { ScoreDashboard } from "@/components/journey/score-dashboard"
import { useDemoHome } from "@/lib/journey/use-demo-home"

import { MakeMyHomeButton } from "./make-my-home-button"

/** Read-only demo home view (CONTRACT §4.1): no login, no household shown. */
export function DemoHomeView({ slug }: { slug: string }) {
  const state = useDemoHome(slug)

  if (state.status === "loading") return <p className="text-muted-foreground">Loading…</p>
  if (state.status === "not_found") return <p role="alert">We couldn&apos;t find that demo home.</p>
  if (state.status === "error") return <p role="alert">{state.error.detail}</p>

  const { home } = state
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-deep text-2xl font-semibold">{home.address.line1}</h1>
          <p className="text-muted-foreground text-sm">
            Demo home · Score {home.score.value} ({home.score.band})
          </p>
        </div>
        <MakeMyHomeButton home={home} />
      </div>
      <RiskView risk={home.risk} address={home.address} />
      <ScoreDashboard score={home.score} property={home.property} />
      <div>
        <h2 className="text-deep mb-3 text-xl font-semibold">Funding</h2>
        <FundingBundleView bundle={home.funding} cost={home.plan.total_cost_low_gbp} />
      </div>
    </>
  )
}
