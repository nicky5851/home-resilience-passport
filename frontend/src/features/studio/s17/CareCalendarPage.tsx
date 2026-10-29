"use client"

import { useEffect, useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { CareCalendar } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { StudioNav } from "@/features/studio/components/StudioNav"

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

export function CareCalendarPage({ homeRef }: { homeRef: string }) {
  const [result, setResult] = useState<CareCalendar | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [subscribeUrl, setSubscribeUrl] = useState<string | null>(null)
  const [subscribeError, setSubscribeError] = useState<unknown>(null)

  const isDemo = homeRef.startsWith("demo-")

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}/care-calendar", { params: { path: { ref: homeRef } } })
      .then(unwrap)
      .then(setResult)
      .catch(setError)
  }, [homeRef])

  async function subscribe() {
    try {
      const res = unwrap(
        await studioApi.POST("/api/v1/studio/homes/{ref}/care-calendar/subscribe", {
          params: { path: { ref: homeRef } },
        }),
      )
      setSubscribeUrl(res.url)
    } catch (e) {
      setSubscribeError(e)
    }
  }

  async function unsubscribe() {
    try {
      await studioApi.DELETE("/api/v1/studio/homes/{ref}/care-calendar/subscribe", {
        params: { path: { ref: homeRef } },
      })
      setSubscribeUrl(null)
    } catch (e) {
      setSubscribeError(e)
    }
  }

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      <h1 className="s-display text-2xl">Home Care Calendar</h1>
      <p>A yearly maintenance plan timed to your home and your local climate.</p>

      {error ? <ErrorState error={error} /> : null}
      {!result && !error ? <p className="s-mono">Reading your local climate…</p> : null}

      {result && (
        <div className="space-y-4">
          <div className="s-card flex flex-wrap items-center gap-4">
            <p className="s-mono text-sm">
              First frost ~{result.climate.first_frost_avg ?? "unknown"} · Last frost ~
              {result.climate.last_frost_avg ?? "unknown"}
            </p>
            <p className="s-mono text-sm">
              Wettest: {MONTH_NAMES[result.climate.wettest_month - 1]} · Windiest:{" "}
              {MONTH_NAMES[result.climate.windiest_month - 1]}
            </p>
            {result.fallback_used ? <FallbackChip /> : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <a
              className="s-focus-ring s-card px-3 py-1.5 underline"
              href={`/api/v1/studio/homes/${homeRef}/care-calendar.ics`}
              download
            >
              Download (.ics)
            </a>
            {!isDemo &&
              (subscribeUrl ? (
                <button
                  type="button"
                  className="s-focus-ring s-card px-3 py-1.5"
                  onClick={unsubscribe}
                >
                  Stop the feed
                </button>
              ) : (
                <button
                  type="button"
                  className="s-focus-ring s-card px-3 py-1.5"
                  onClick={subscribe}
                >
                  Subscribe on this phone
                </button>
              ))}
          </div>
          {subscribeUrl ? (
            <p className="s-mono text-xs break-all">
              Feed URL: <a href={subscribeUrl}>{subscribeUrl}</a>
            </p>
          ) : null}
          {subscribeError ? <ErrorState error={subscribeError} /> : null}

          <div className="space-y-3">
            {result.months.map((month) => (
              <div key={month.month} className="s-card">
                <p className="s-eyebrow">{MONTH_NAMES[month.month - 1]}</p>
                {month.tasks.length === 0 ? (
                  <p className="s-mono text-sm opacity-60">Nothing scheduled.</p>
                ) : (
                  <ul className="space-y-2">
                    {month.tasks.map((task) => (
                      <li key={task.id}>
                        <p className="font-semibold">
                          {task.title}{" "}
                          <span className="s-mono text-xs opacity-60">
                            ({task.effort_minutes} min)
                          </span>
                        </p>
                        <p className="text-sm opacity-80">{task.why}</p>
                        <a
                          className="s-focus-ring s-mono text-xs underline"
                          href={task.guidance_url}
                        >
                          Guidance
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
