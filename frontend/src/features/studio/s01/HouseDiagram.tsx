"use client"

import { useId } from "react"

import type { HotspotId } from "@/features/studio/api/types"

const REGIONS: { id: HotspotId; label: string; path: string }[] = [
  { id: "roof", label: "Roof", path: "M38 92 L150 18 L262 92 Z" },
  { id: "walls", label: "Walls", path: "M52 92 H248 V208 H52 Z" },
  { id: "windows", label: "Windows", path: "M74 112 H122 V158 H74 Z" },
  { id: "door", label: "Door", path: "M142 138 H180 V208 H142 Z" },
  { id: "ground", label: "Garden & drainage", path: "M18 208 H282 V226 H18 Z" },
  { id: "services", label: "Services", path: "M198 158 H236 V208 H198 Z" },
]

/** One illustrated house, six clickable hotspots. A region gets a brass glow and a soft green
 * wash once a measure there is applied, on top of the painted scene (not a flat recolour), so
 * the house still reads as a house once things light up. */
export function HouseDiagram({
  active,
  onSelect,
}: {
  active: Set<HotspotId>
  onSelect?: (hotspot: HotspotId) => void
}) {
  const uid = useId()
  const id = (name: string) => `${uid}-${name}`

  return (
    <svg viewBox="0 0 300 240" className="h-auto w-full" role="img" aria-label="Your home">
      <defs>
        <linearGradient id={id("sky")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--s-sky-top)" />
          <stop offset="100%" stopColor="var(--s-sky-bottom)" />
        </linearGradient>
        <linearGradient id={id("grass")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--s-grass-top)" />
          <stop offset="100%" stopColor="var(--s-grass-bottom)" />
        </linearGradient>
        <linearGradient id={id("roof")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--s-roof-top)" />
          <stop offset="100%" stopColor="var(--s-roof-bottom)" />
        </linearGradient>
        <pattern id={id("brick")} width="28" height="14" patternUnits="userSpaceOnUse">
          <rect width="28" height="14" fill="var(--s-brick)" />
          <path
            d="M0 0 H28 M0 7 H28 M0 14 H28 M7 0 V7 M21 0 V7 M0 7 V14 M14 7 V14 M28 7 V14"
            stroke="var(--s-brick-mortar)"
            strokeWidth="1"
            fill="none"
          />
        </pattern>
        <linearGradient id={id("glass")} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--s-glass-top)" />
          <stop offset="100%" stopColor="var(--s-glass-bottom)" />
        </linearGradient>
        <linearGradient id={id("wood")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--s-wood-top)" />
          <stop offset="100%" stopColor="var(--s-wood-bottom)" />
        </linearGradient>
        <radialGradient id={id("shadow")} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="var(--s-ink)" stopOpacity="0.18" />
          <stop offset="100%" stopColor="var(--s-ink)" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* backdrop */}
      <rect x="0" y="0" width="300" height="240" fill={`url(#${id("sky")})`} rx="20" />
      <circle cx="258" cy="36" r="16" fill="var(--s-sun)" opacity="0.8" />
      <rect x="0" y="208" width="300" height="32" fill={`url(#${id("grass")})`} />
      <ellipse cx="150" cy="222" rx="128" ry="10" fill={`url(#${id("shadow")})`} />

      {/* chimney (decorative, not a hotspot) */}
      <rect x="205" y="34" width="16" height="30" fill="var(--s-brick)" />
      <rect x="203" y="30" width="20" height="6" fill="var(--s-brick-mortar)" />

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
            {renderRegion(r, id)}
            <path
              d={r.path}
              fill="var(--s-green-500)"
              fillOpacity={isActive ? 0.28 : 0}
              stroke={isActive ? "#ffffff" : "transparent"}
              strokeWidth={isActive ? 4 : 0}
              strokeDasharray={isActive ? "7 4" : undefined}
              style={{
                transition: "fill-opacity 320ms var(--s-ease-out), stroke 320ms var(--s-ease-out)",
                filter: isActive ? "drop-shadow(0 0 3px rgba(0,0,0,0.55))" : undefined,
              }}
            />
            {isActive && (
              <path
                d={r.path}
                fill="none"
                stroke="var(--s-brass)"
                strokeWidth="2"
                strokeDasharray="7 4"
                strokeDashoffset="5.5"
              />
            )}
          </g>
        )
      })}

      {/* garden flourishes, drawn above the ground hotspot outline so clicks still land */}
      <circle cx="50" cy="214" r="7" fill="var(--s-green-700)" opacity="0.5" />
      <circle cx="262" cy="216" r="6" fill="var(--s-green-700)" opacity="0.5" />
      <rect x="110" y="210" width="60" height="4" rx="2" fill="var(--s-path)" opacity="0.8" />
    </svg>
  )
}

function renderRegion(r: { id: HotspotId; path: string }, id: (name: string) => string) {
  switch (r.id) {
    case "roof":
      return (
        <>
          <path d={r.path} fill={`url(#${id("roof")})`} />
          <path d="M44 88 L150 24 L256 88" stroke="var(--s-roof-bottom)" strokeWidth="2" fill="none" />
          <path d="M150 18 L150 92" stroke="var(--s-roof-bottom)" strokeWidth="1.5" opacity="0.5" />
        </>
      )
    case "walls":
      return (
        <>
          <path d={r.path} fill={`url(#${id("brick")})`} />
          <path d={r.path} fill="none" stroke="var(--s-stone-200)" strokeWidth="1.5" />
        </>
      )
    case "windows":
      return (
        <>
          <rect x="70" y="108" width="56" height="54" rx="3" fill="var(--s-wood-bottom)" />
          <rect x="74" y="112" width="48" height="46" fill={`url(#${id("glass")})`} />
          <path d="M98 112 V158 M74 135 H122" stroke="var(--s-wood-bottom)" strokeWidth="2" />
          <rect x="70" y="162" width="56" height="6" rx="1.5" fill="var(--s-brass)" opacity="0.7" />
        </>
      )
    case "door":
      return (
        <>
          <path d={r.path} fill={`url(#${id("wood")})`} />
          <path d="M148 146 H174 M148 164 H174 M148 182 H174" stroke="var(--s-wood-bottom)" strokeWidth="1.5" />
          <circle cx="172" cy="178" r="2.6" fill="var(--s-brass)" />
        </>
      )
    case "ground":
      return (
        <>
          <path d={r.path} fill="var(--s-path)" opacity="0.9" />
          <path d={r.path} fill="none" stroke="var(--s-stone-200)" strokeWidth="1" />
        </>
      )
    case "services":
      return (
        <>
          <rect x="198" y="158" width="38" height="50" rx="3" fill="var(--s-card)" stroke="var(--s-stone-200)" />
          <rect x="203" y="164" width="28" height="10" rx="2" fill="var(--s-stone-200)" />
          <rect x="203" y="178" width="28" height="10" rx="2" fill="var(--s-stone-200)" />
          <rect x="203" y="192" width="28" height="10" rx="2" fill="var(--s-stone-200)" />
        </>
      )
    default:
      return null
  }
}

export const HOUSE_REGIONS = REGIONS
