import { Suspense } from "react"

import { HomeFunding } from "./home-funding"

export const metadata = { title: "Your funding · Home Resilience Passport" }

export default async function FundingPage({ params }: { params: Promise<{ home_id: string }> }) {
  const { home_id } = await params
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Your funding</h1>
      <Suspense>
        <HomeFunding homeId={home_id} />
      </Suspense>
    </section>
  )
}
