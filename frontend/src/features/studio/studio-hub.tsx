"use client"

import Link from "next/link"
import { useEffect, useState } from "react"

import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { DemoHome, HomeSummary } from "@/lib/api/types"

import { EmptyState } from "@/features/studio/components/EmptyState"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { Reveal } from "@/features/studio/components/Reveal"
import { SkeletonBlock } from "@/features/studio/components/SkeletonBlock"
import { studioApi, unwrap as studioUnwrap } from "@/features/studio/api/client"
import type { FeatureMeta } from "@/features/studio/api/types"

/** Features with no home ref: they work on arbitrary addresses (S18) or a portfolio sample
 * (S20), so they get their own standalone page instead of `/studio/{ref}/{id}-{slug}`. */
const STANDALONE_PATH: Record<string, string> = {
  s18: "/studio/compare",
  s20: "/studio/portfolio",
}

const CHAPTER_LABEL: Record<string, string> = {
  understand: "Understand",
  measure: "Measure",
  plan: "Plan",
  live: "Live",
  money: "Money",
  ask: "Ask",
}

export function StudioHub({ homeRef }: { homeRef?: string }) {
  const [features, setFeatures] = useState<FeatureMeta[] | null>(null)
  const [demos, setDemos] = useState<DemoHome[] | null>(null)
  const [myHomes, setMyHomes] = useState<HomeSummary[] | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi.GET("/api/v1/studio/features").then(studioUnwrap).then(setFeatures).catch(setError)
    if (!homeRef) {
      api.GET("/api/v1/demo/homes").then(unwrap).then(setDemos).catch(setError)
      api
        .GET("/api/v1/homes")
        .then(unwrap)
        .then(setMyHomes)
        .catch((e: unknown) => {
          if (!isApiError(e) || e.code !== "unauthorised") setError(e)
        })
    }
  }, [homeRef])

  if (error) return <ErrorState error={error} />

  return (
    <div className="space-y-10">
      <section className="s-stage s-reveal rounded-3xl p-10" style={{ color: "var(--s-paper)" }}>
        <p className="s-eyebrow">Resilience Studio</p>
        <h1 className="s-display mt-2 text-4xl" style={{ color: "var(--s-paper)" }}>
          Twenty ways to see your home&apos;s future, clearly.
        </h1>
        <p className="mt-3 max-w-xl" style={{ color: "var(--s-paper)" }}>
          Every number is labelled: measured, officially modelled, or our own estimate. Nothing here
          is a valuation or a guarantee.
        </p>
      </section>

      {!homeRef && (
        <section className="space-y-3">
          <h2 className="s-display text-xl">Pick a home</h2>
          {myHomes && myHomes.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              {myHomes.map((h) => (
                <li key={h.home_id}>
                  <Link
                    href={`/studio/${h.home_id}`}
                    className="s-focus-ring rounded-full px-3 py-1 text-sm"
                    style={{ background: "var(--s-green-100)", color: "var(--s-green-700)" }}
                  >
                    {h.line1}
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
          {!demos ? (
            <SkeletonBlock height={80} />
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {demos.map((d, i) => (
                <li key={d.slug}>
                  <Reveal index={i}>
                    <Link href={`/studio/demo-${d.slug}`} className="s-card s-focus-ring block">
                      <p className="s-eyebrow">Demo</p>
                      <p className="mt-1 font-medium">{d.address.line1}</p>
                      <p className="text-sm" style={{ color: "var(--s-stone-500)" }}>
                        {d.address.postcode}
                      </p>
                    </Link>
                  </Reveal>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="space-y-6">
        {!features ? (
          <SkeletonBlock height={200} />
        ) : features.length === 0 ? (
          <EmptyState title="No features are enabled yet." />
        ) : (
          Object.entries(
            features.reduce<Record<string, FeatureMeta[]>>((acc, f) => {
              ;(acc[f.chapter] ??= []).push(f)
              return acc
            }, {}),
          ).map(([chapter, group]) => (
            <div key={chapter} id={chapter} className="space-y-3">
              <h2 className="s-display text-xl">{CHAPTER_LABEL[chapter] ?? chapter}</h2>
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {group.map((f, i) => (
                  <li key={f.id}>
                    <Reveal index={i}>
                      <Link
                        href={
                          STANDALONE_PATH[f.id] ??
                          (homeRef ? `/studio/${homeRef}/${f.id}-${f.slug}` : "/studio")
                        }
                        className="s-card s-focus-ring block"
                        aria-disabled={!(f.id in STANDALONE_PATH) && !homeRef}
                      >
                        <p className="s-mono">
                          {f.id.toUpperCase()} · {f.needs_login ? "sign in" : "open to all"}
                        </p>
                        <p className="s-display mt-1 text-lg">{f.title}</p>
                        <p className="mt-1 text-sm" style={{ color: "var(--s-stone-500)" }}>
                          {f.pitch}
                        </p>
                      </Link>
                    </Reveal>
                  </li>
                ))}
              </ul>
            </div>
          ))
        )}
      </section>
    </div>
  )
}
