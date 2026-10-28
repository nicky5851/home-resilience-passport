import { Suspense } from "react"

import { HouseholdForm } from "./household-form"

export const metadata = { title: "About your household · Home Resilience Passport" }

export default function HouseholdPage() {
  return (
    <section className="max-w-xl space-y-6">
      <div className="space-y-2">
        <h1 className="text-deep text-2xl font-semibold">About your household</h1>
        <p className="text-muted-foreground">
          This helps us pick the right funding and order your plan sensibly. Nothing here is
          shared with anyone else, and it is never sent to the AI that writes your plan&apos;s
          explanations.
        </p>
      </div>
      <Suspense>
        <HouseholdForm />
      </Suspense>
    </section>
  )
}
