"use client"

import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useEffect } from "react"

import type { UserRead } from "@/lib/api/types"
import { loginPath, useUser } from "@/lib/auth/use-user"

/** Renders children only for a logged-in user; redirects to /login?next=... on 401. */
export function RequireUser({ children }: { children: (user: UserRead) => React.ReactNode }) {
  const state = useUser()
  const router = useRouter()
  const pathname = usePathname()
  const search = useSearchParams().toString()

  useEffect(() => {
    if (state.status === "anonymous")
      router.replace(loginPath(search ? `${pathname}?${search}` : pathname))
  }, [state.status, router, pathname, search])

  if (state.status === "authenticated") return children(state.user)
  if (state.status === "error") return <p role="alert">{state.error.detail}</p>
  return <p className="text-muted-foreground">Loading…</p>
}
