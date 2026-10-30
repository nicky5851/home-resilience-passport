/** Normalises every "how bad is this" word Studio's APIs use (risk levels, carbon-intensity
 * index, air-quality bands, heat-loss ratings, solar suitability, …) onto the three-colour
 * red/amber/green signal (`tokens.css`'s `--s-risk-*`), so the same word always gets the same
 * colour everywhere, instead of each feature inventing its own low/medium/high palette. */

export type RagBand = "low" | "medium" | "high"

const LOW = new Set(["none", "very low", "low", "excellent", "good"])
const HIGH = new Set(["very high", "very_high", "high", "poor"])

/** `undefined` for a word this doesn't recognise as a severity (e.g. "freeholder_needed") -
 * callers should fall back to a neutral tone rather than guessing. */
export function ragBand(value: string | null | undefined): RagBand | undefined {
  if (!value) return undefined
  const v = value.toLowerCase().trim()
  if (LOW.has(v)) return "low"
  if (HIGH.has(v)) return "high"
  if (v === "medium" || v === "moderate" || v === "average" || v === "fair") return "medium"
  return undefined
}

export const RAG_COLOR: Record<RagBand, string> = {
  low: "var(--s-risk-low)",
  medium: "var(--s-risk-med)",
  high: "var(--s-risk-high)",
}

/** Falls back to a neutral stone colour for a word `ragBand` doesn't recognise. */
export function ragColor(value: string | null | undefined): string {
  const band = ragBand(value)
  return band ? RAG_COLOR[band] : "var(--s-stone-500)"
}
