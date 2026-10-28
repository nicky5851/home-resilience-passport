"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"

export function ForgotPasswordForm() {
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const email = String(new FormData(e.currentTarget).get("email"))
    setBusy(true)
    setError(null)
    try {
      unwrap(await api.POST("/api/v1/auth/forgot-password", { body: { email } }))
      setSent(true)
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Something went wrong. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  if (sent) {
    return (
      <p role="status">
        If that email address has an account, we have sent a link to reset your password.
      </p>
    )
  }

  return (
    <form onSubmit={onSubmit} className="max-w-sm space-y-4" noValidate>
      <div className="space-y-1">
        <label htmlFor="email" className="block text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          className="border-input w-full rounded-md border px-3 py-2"
        />
      </div>
      {error && (
        <p role="alert" className="text-risk text-sm">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy}>
        {busy ? "Sending…" : "Send reset link"}
      </Button>
    </form>
  )
}
