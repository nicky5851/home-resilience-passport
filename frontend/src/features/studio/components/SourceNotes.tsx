import type { Evidence } from "@/features/studio/api/evidence"
import { formatDate } from "@/features/studio/lib/format"

/** Numbered footnotes at the end of every feature page (docs/studio/N_20_function.md §2.3). */
export function SourceNotes({ evidence }: { evidence: Evidence[] }) {
  if (evidence.length === 0) return null
  return (
    <ol className="s-mono space-y-1 border-t pt-4" style={{ borderColor: "var(--s-stone-200)" }}>
      {evidence.map((e, i) => (
        <li key={`${e.label}-${i}`}>
          [{i + 1}] {e.label} — {e.source}, retrieved {formatDate(e.retrieved_at)}.{" "}
          <a href={e.source_url} target="_blank" rel="noreferrer" className="underline">
            Source
          </a>
          {e.note ? ` · ${e.note}` : ""}
        </li>
      ))}
    </ol>
  )
}
