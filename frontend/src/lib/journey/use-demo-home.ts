"use client"

import { useEffect, useState } from "react"

import { api, unwrap } from "@/lib/api/client"
import { ApiError } from "@/lib/api/errors"
import type { DemoHome } from "@/lib/api/types"

type State =
  | { status: "loading"; home: null; error: null }
  | { status: "ready"; home: DemoHome; error: null }
  | { status: "not_found"; home: null; error: null }
  | { status: "error"; home: null; error: ApiError }

/** Finds one demo home by slug from `GET /demo/homes` (CONTRACT §4.1: read-only, no login). */
export function useDemoHome(slug: string): State {
  const [state, setState] = useState<State>({ status: "loading", home: null, error: null })

  useEffect(() => {
    let cancelled = false
    api
      .GET("/api/v1/demo/homes")
      .then(unwrap)
      .then((homes) => {
        if (cancelled) return
        const home = homes.find((h) => h.slug === slug)
        setState(
          home
            ? { status: "ready", home, error: null }
            : { status: "not_found", home: null, error: null },
        )
      })
      .catch((e: unknown) => {
        if (cancelled) return
        const err = e instanceof ApiError ? e : ApiError.from(0, null)
        setState({ status: "error", home: null, error: err })
      })
    return () => {
      cancelled = true
    }
  }, [slug])

  return state
}
