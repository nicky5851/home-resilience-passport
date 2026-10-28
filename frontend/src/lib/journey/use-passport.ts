"use client"

import { useEffect, useState } from "react"

import { api, unwrap } from "@/lib/api/client"
import { ApiError } from "@/lib/api/errors"
import type { Passport } from "@/lib/api/types"

type State =
  | { status: "loading"; passport: null; error: null }
  | { status: "ready"; passport: Passport; error: null }
  | { status: "error"; passport: null; error: ApiError }

/** `GET /homes/{id}/passport`: address, household, property, latest risk, latest score, plan. */
export function usePassport(homeId: string): State {
  const [state, setState] = useState<State>({ status: "loading", passport: null, error: null })

  useEffect(() => {
    let cancelled = false
    api
      .GET("/api/v1/homes/{home_id}/passport", { params: { path: { home_id: homeId } } })
      .then(unwrap)
      .then((passport) => {
        if (!cancelled) setState({ status: "ready", passport, error: null })
      })
      .catch((e: unknown) => {
        if (cancelled) return
        const err = e instanceof ApiError ? e : ApiError.from(0, null)
        setState({ status: "error", passport: null, error: err })
      })
    return () => {
      cancelled = true
    }
  }, [homeId])

  return state
}
