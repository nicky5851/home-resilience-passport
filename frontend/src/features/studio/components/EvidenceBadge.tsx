"use client"

import { EVIDENCE_LABEL, EVIDENCE_VAR, type Evidence } from "@/features/studio/api/evidence"
import { formatDate } from "@/features/studio/lib/format"

const SHAPE: Record<Evidence["evidence"], string> = {
  observed: "●",
  official_modelled: "◐",
  estimated: "◌",
}

/** Shape + word + tooltip with source, date and link (docs/studio/N_20_function.md §2.5). */
export function EvidenceBadge({ evidence }: { evidence: Evidence }) {
  return (
    <span
      className="s-focus-ring inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs"
      style={{ borderColor: "var(--s-stone-200)", color: EVIDENCE_VAR[evidence.evidence] }}
      title={`${evidence.source} · retrieved ${formatDate(evidence.retrieved_at)}${
        evidence.note ? ` · ${evidence.note}` : ""
      }`}
      tabIndex={0}
    >
      <span aria-hidden="true">{SHAPE[evidence.evidence]}</span>
      {EVIDENCE_LABEL[evidence.evidence]}
    </span>
  )
}
