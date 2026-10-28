"use client"

import { useEffect, useState } from "react"

import { ErrorState } from "@/features/studio/components/ErrorState"
import { HomeChip } from "@/features/studio/components/HomeChip"
import { SkeletonBlock } from "@/features/studio/components/SkeletonBlock"
import { StudioNav } from "@/features/studio/components/StudioNav"
import { studioApi, unwrap } from "@/features/studio/api/client"
import type { StudioHomeSummary } from "@/features/studio/api/types"
import { StudioHub } from "@/features/studio/studio-hub"

export function StudioHomeHub({ homeRef }: { homeRef: string }) {
  const [home, setHome] = useState<StudioHomeSummary | null>(null)
  const [error, setError] = useState<unknown>(null)

  useEffect(() => {
    studioApi
      .GET("/api/v1/studio/homes/{ref}", { params: { path: { ref: homeRef } } })
      .then(unwrap)
      .then(setHome)
      .catch(setError)
  }, [homeRef])

  if (error) return <ErrorState error={error} />

  return (
    <div className="space-y-6">
      <StudioNav ref={homeRef} />
      {!home ? (
        <SkeletonBlock height={40} />
      ) : (
        <HomeChip
          line1={home.line1}
          postcodeDistrict={home.postcode_district}
          isDemo={home.is_demo}
        />
      )}
      <StudioHub homeRef={homeRef} />
    </div>
  )
}
