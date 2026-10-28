"use client"

import type { HotspotId } from "@/features/studio/api/types"

const REGIONS: { id: HotspotId; label: string; path: string; labelPos: [number, number] }[] = [
  { id: "roof", label: "Roof", path: "M40 90 L150 20 L260 90 Z", labelPos: [150, 55] },
  { id: "walls", label: "Walls", path: "M50 90 H250 V210 H50 Z", labelPos: [230, 100] },
  { id: "windows", label: "Windows", path: "M75 115 H120 V160 H75 Z", labelPos: [97, 137] },
  { id: "door", label: "Door", path: "M140 140 H180 V210 H140 Z", labelPos: [160, 180] },
  {
    id: "ground",
    label: "Garden & drainage",
    path: "M20 210 H280 V225 H20 Z",
    labelPos: [275, 217],
  },
  { id: "services", label: "Services", path: "M200 160 H235 V210 H200 Z", labelPos: [217, 185] },
]

/** One schematic house, six clickable hotspots. A region lights up (fill + ring) once a measure
 * there is applied — simpler than per-measure illustration, same interaction model. */
export function HouseDiagram({
  active,
  onSelect,
}: {
  active: Set<HotspotId>
  onSelect?: (hotspot: HotspotId) => void
}) {
  return (
    <svg viewBox="0 0 300 235" className="h-auto w-full" role="img" aria-label="Your home">
      <rect x="0" y="0" width="300" height="235" fill="none" />
      {REGIONS.map((r) => {
        const isActive = active.has(r.id)
        return (
          <g
            key={r.id}
            onClick={() => onSelect?.(r.id)}
            style={{ cursor: onSelect ? "pointer" : "default" }}
            tabIndex={onSelect ? 0 : undefined}
            role={onSelect ? "button" : undefined}
            aria-label={r.label}
            aria-pressed={isActive}
            className="s-focus-ring"
          >
            <path
              d={r.path}
              fill={isActive ? "var(--s-green-500)" : "var(--s-card)"}
              fillOpacity={isActive ? 0.85 : 1}
              stroke={isActive ? "var(--s-brass)" : "var(--s-stone-200)"}
              strokeWidth={isActive ? 2.5 : 1.5}
              style={{ transition: "fill 320ms var(--s-ease-out), stroke 320ms var(--s-ease-out)" }}
            />
          </g>
        )
      })}
    </svg>
  )
}

export const HOUSE_REGIONS = REGIONS
