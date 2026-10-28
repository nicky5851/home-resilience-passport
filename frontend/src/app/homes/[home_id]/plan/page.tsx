import { Suspense } from "react"

import { HomePlan } from "./home-plan"

export const metadata = { title: "Your improvement plan · Home Resilience Passport" }

export default async function PlanPage({ params }: { params: Promise<{ home_id: string }> }) {
  const { home_id } = await params
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Your improvement plan</h1>
      <Suspense>
        <HomePlan homeId={home_id} />
      </Suspense>
    </section>
  )
}
