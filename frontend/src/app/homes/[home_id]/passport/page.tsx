import { Suspense } from "react"

import { HomePassportPage } from "./home-passport"

export const metadata = { title: "Your passport · Home Resilience Passport" }

export default async function PassportPage({ params }: { params: Promise<{ home_id: string }> }) {
  const { home_id } = await params
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Your passport</h1>
      <Suspense>
        <HomePassportPage homeId={home_id} />
      </Suspense>
    </section>
  )
}
