"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"

export function ResetPasswordForm() {
  const router = useRouter()
  const token = useSearchParams().get("token") ?? ""
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const password = String(new FormData(e.currentTarget).get("password"))
    setBusy(true)
    setError(null)
    try {
      unwrap(await api.POST("/api/v1/auth/reset-password", { body: { token, password } }))
      router.replace("/login")
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Something went wrong. Please try again.")
      setBusy(false)
    }
  }

  if (!token) {
    return <p role="alert">This reset link is missing its token. Please request a new one.</p>
  }

  return (
    <form onSubmit={onSubmit} className="max-w-sm space-y-4" noValidate>
      <div className="space-y-1">
        <label htmlFor="password" className="block text-sm font-medium">
          New password
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
      {error && (
        <p role="alert" className="text-risk text-sm">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : "Reset password"}
      </Button>
    </form>
  )
}
