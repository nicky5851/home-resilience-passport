import type { Evidence } from "@/features/studio/api/evidence"

import { EvidenceBadge } from "@/features/studio/components/EvidenceBadge"

export function StatTile(props: {
  eyebrow: string
  value: string
  unit?: string
  delta?: string
  evidence?: Evidence
}) {
  return (
    <div className="s-card" role="group" aria-label={props.eyebrow}>
      <div className="s-eyebrow">{props.eyebrow}</div>
      <div className="s-display mt-1 text-3xl" aria-live="polite">
        {props.value}
        {props.unit ? (
          <span className="ml-1 text-base" style={{ color: "var(--s-stone-500)" }}>
            {props.unit}
          </span>
        ) : null}
      </div>
      {props.delta ? (
        <div className="mt-1 text-sm" style={{ color: "var(--s-green-700)" }}>
          {props.delta}
        </div>
      ) : null}
      {props.evidence ? (
        <div className="mt-3">
          <EvidenceBadge evidence={props.evidence} />
        </div>
      ) : null}
    </div>
  )
}
