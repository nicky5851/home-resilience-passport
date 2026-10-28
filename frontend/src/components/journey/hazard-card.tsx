import type { HazardLevel } from "@/lib/api/types"

const HAZARD_LABEL: Record<HazardLevel["hazard"], string> = {
  river_sea_flood: "River and sea flooding",
  overheating: "Overheating",
  storm: "Storm",
  subsidence: "Subsidence",
  surface_water: "Surface water flooding",
}

const LEVEL_LABEL: Record<HazardLevel["today"], string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
}

const LEVEL_CLASS: Record<HazardLevel["today"], string> = {
  low: "bg-level-low/15 text-level-low",
  medium: "bg-level-medium/15 text-level-medium",
  high: "bg-level-high/15 text-level-high",
}

/** One hazard, today or in 2050 depending on `when` (spec L9). */
export function HazardCard({ level, when }: { level: HazardLevel; when: "today" | "y2050" }) {
  const value = level[when]
  return (
    <article className="border-border space-y-2 rounded-lg border p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-medium">{HAZARD_LABEL[level.hazard]}</h3>
        <span
          className={`rounded-full px-2.5 py-0.5 text-sm font-semibold ${LEVEL_CLASS[value]}`}
        >
          {LEVEL_LABEL[value]}
        </span>
      </div>
      <p className="text-sm">{level.why}</p>
      <p className="text-muted-foreground text-xs">Source: {level.data_source}</p>
    </article>
  )
}
