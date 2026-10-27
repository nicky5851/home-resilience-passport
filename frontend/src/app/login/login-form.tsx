"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, login } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import { safeNext } from "@/lib/auth/use-user"

// Minimal log-in form so the auth guard has somewhere to send people. L13 adds sign-up,
// forgot-password and the full account pages.
export function LoginForm() {
  const router = useRouter()
  const next = safeNext(useSearchParams().get("next"))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    setBusy(true)
    setError(null)
    try {
      await login(api, String(form.get("email")), String(form.get("password")))
      router.replace(next)
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Something went wrong. Please try again.")
      setBusy(false)
    }
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
      <div className="space-y-1">
        <label htmlFor="password" className="block text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
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
        {busy ? "Logging in…" : "Log in"}
      </Button>
    </form>
  )
}
