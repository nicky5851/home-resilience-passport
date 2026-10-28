import { Suspense } from "react"

import { SignupForm } from "./signup-form"

export const metadata = { title: "Sign up · Home Resilience Passport" }

export default function SignupPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Sign up</h1>
      <Suspense>
        <SignupForm />
      </Suspense>
    </section>
  )
}
