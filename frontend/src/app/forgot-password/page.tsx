import { ForgotPasswordForm } from "./forgot-password-form"

export const metadata = { title: "Forgot password · Home Resilience Passport" }

export default function ForgotPasswordPage() {
  return (
    <section className="space-y-6">
      <h1 className="text-deep text-2xl font-semibold">Forgot your password?</h1>
      <ForgotPasswordForm />
    </section>
  )
}
