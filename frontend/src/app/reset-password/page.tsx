import { Suspense } from "react"

import { ResetPasswordForm } from "./reset-password-form"

export const metadata = { title: "Reset password · Home Resilience Passport" }

export default function ResetPasswordPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Reset your password</h1>
      <Suspense>
        <ResetPasswordForm />
      </Suspense>
    </section>
  )
}
