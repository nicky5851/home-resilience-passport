"use client"

import { useCallback, useEffect, useState } from "react"

import { api, unwrap } from "@/lib/api/client"
import { ApiError } from "@/lib/api/errors"
import type { UserRead } from "@/lib/api/types"

type State =
  | { status: "loading"; user: null }
  | { status: "authenticated"; user: UserRead }
  | { status: "anonymous"; user: null }
  | { status: "error"; user: null; error: ApiError }

/** The logged-in user from GET /users/me (CONTRACT §4). `anonymous` on 401. */
export function useUser(): State & { refresh: () => Promise<void> } {
  const [state, setState] = useState<State>({ status: "loading", user: null })

  const refresh = useCallback(async () => {
    try {
      const user = unwrap(await api.GET("/api/v1/users/me"))
      setState({ status: "authenticated", user })
    } catch (e) {
      const err = e instanceof ApiError ? e : ApiError.from(0, null)
      setState(
        err.status === 401
          ? { status: "anonymous", user: null }
          : { status: "error", user: null, error: err },
      )
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { ...state, refresh }
}

/** Where to send a logged-out visitor so they come back afterwards. */
export function loginPath(next: string): string {
  return `/login?next=${encodeURIComponent(next)}`
}

/** Only allow same-site relative paths as `next`, never another domain. */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//")) return "/"
  return next
}
