import { Suspense } from "react"

import { DemoHomesButton } from "./demo-homes"
import { StartForm } from "./start-form"

export const metadata = { title: "Find your home · Home Resilience Passport" }

export default function StartPage() {
  return (
    <section className="max-w-xl space-y-8">
      <div className="space-y-2">
        <h1 className="text-deep text-2xl font-semibold">Find your home</h1>
        <p className="text-muted-foreground">
          Enter your postcode and we will look up your address and energy certificate.
        </p>
      </div>
      <Suspense>
        <StartForm />
      </Suspense>
      <div className="border-border border-t pt-6">
        <p className="text-muted-foreground mb-3 text-sm">
          Not ready to enter your own address?
        </p>
        <Suspense>
          <DemoHomesButton />
        </Suspense>
      </div>
    </section>
  )
}
