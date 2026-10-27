import { Suspense } from "react"

import { MyHomes } from "./my-homes"

export const metadata = { title: "My homes · Home Resilience Passport" }

export default function HomesPage() {
  return (
    <section className="space-y-4">
      <h1 className="text-deep text-2xl font-semibold">My homes</h1>
      <Suspense>
        <MyHomes />
      </Suspense>
    </section>
  )
}
