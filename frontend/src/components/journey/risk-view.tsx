"use client"

import dynamic from "next/dynamic"
import { useState } from "react"

import { HazardCard } from "@/components/journey/hazard-card"
import type { RiskProfile } from "@/lib/api/types"

const HomeMap = dynamic(
  () => import("@/components/journey/home-map").then((m) => m.HomeMap),
  { ssr: false, loading: () => <div className="bg-mint h-64 w-full animate-pulse rounded-lg" /> },
)

/** The risk page body (spec L9): map, hazard cards, Today / 2050 toggle. */
export function RiskView({
  risk,
  address,
}: {
  risk: RiskProfile
  address: { lat: number; lon: number; line1: string }
}) {
  const [when, setWhen] = useState<"today" | "y2050">("today")

  return (
    <div className="space-y-6">
      <HomeMap lat={address.lat} lon={address.lon} label={address.line1} />

      <div
        role="group"
        aria-label="Show risks for"
        className="border-border inline-flex rounded-md border p-0.5 text-sm"
      >
        {(["today", "y2050"] as const).map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={when === option}
            onClick={() => setWhen(option)}
            className={`rounded-sm px-3 py-1.5 font-medium transition-colors ${
              when === option ? "bg-deep text-white" : "text-muted-foreground"
            }`}
          >
            {option === "today" ? "Today" : "2050"}
          </button>
        ))}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {risk.levels.map((level) => (
          <HazardCard key={level.hazard} level={level} when={when} />
        ))}
      </div>
    </div>
  )
}
