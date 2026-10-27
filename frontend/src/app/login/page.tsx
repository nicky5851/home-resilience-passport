import { Suspense } from "react"

import { LoginForm } from "./login-form"

export const metadata = { title: "Log in · Home Resilience Passport" }

export default function LoginPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Log in</h1>
      <Suspense>
        <LoginForm />
      </Suspense>
    </section>
  )
}
