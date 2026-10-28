export type EvidenceClass = "observed" | "official_modelled" | "estimated"

export type Evidence = {
  label: string
  evidence: EvidenceClass
  source: string
  source_url: string
  retrieved_at: string
  note?: string | null
}

export const EVIDENCE_LABEL: Record<EvidenceClass, string> = {
  observed: "Observed",
  official_modelled: "Official modelled",
  estimated: "Estimated by HRP",
}

export const EVIDENCE_VAR: Record<EvidenceClass, string> = {
  observed: "var(--s-observed)",
  official_modelled: "var(--s-official)",
  estimated: "var(--s-estimated)",
}
