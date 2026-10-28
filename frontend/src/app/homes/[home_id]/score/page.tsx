import { Suspense } from "react"

import { HomeScore } from "./home-score"

export const metadata = { title: "Your Resilience Score · Home Resilience Passport" }

export default async function ScorePage({ params }: { params: Promise<{ home_id: string }> }) {
  const { home_id } = await params
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Your Resilience Score</h1>
      <Suspense>
        <HomeScore homeId={home_id} />
      </Suspense>
    </section>
  )
}
