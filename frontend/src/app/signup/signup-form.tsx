"use client"

import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, login, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import { safeNext } from "@/lib/auth/use-user"

/** Sign-up (spec L13): requires ticking "I have read the privacy notice". */
export function SignupForm() {
  const router = useRouter()
  const next = safeNext(useSearchParams().get("next"))
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const email = String(form.get("email"))
    const password = String(form.get("password"))
    const acceptPrivacy = form.get("accept_privacy") === "on"
    if (!acceptPrivacy) {
      setError("Please confirm you have read the privacy notice.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      unwrap(
        await api.POST("/api/v1/auth/register", {
          body: { email, password, accept_privacy: true },
        }),
      )
      await login(api, email, password)
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
          autoComplete="new-password"
          required
          minLength={8}
          className="border-input w-full rounded-md border px-3 py-2"
        />
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" name="accept_privacy" required />
        <span>
          I have read the{" "}
          <Link href="/privacy" className="text-deep underline underline-offset-4">
            privacy notice
          </Link>
          .
        </span>
      </label>
      {error && (
        <p role="alert" className="text-risk text-sm">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy}>
        {busy ? "Signing up…" : "Sign up"}
      </Button>
    </form>
  )
}
