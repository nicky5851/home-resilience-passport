import { Suspense } from "react"

import { HomeRisk } from "./home-risk"

export const metadata = { title: "Your risks · Home Resilience Passport" }

export default async function RiskPage({ params }: { params: Promise<{ home_id: string }> }) {
  const { home_id } = await params
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Your risks</h1>
      <Suspense>
        <HomeRisk homeId={home_id} />
      </Suspense>
    </section>
  )
}
