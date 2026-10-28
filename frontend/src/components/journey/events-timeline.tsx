import type { PassportEvent } from "@/lib/api/types"

const KIND_LABEL: Record<PassportEvent["kind"], string> = {
  assessed: "Home assessed",
  plan_saved: "Plan updated",
  work_recorded: "Work recorded",
  shared: "Passport shared",
}

function describe(e: PassportEvent): string {
  if (e.kind === "work_recorded") {
    const d = e.detail as { measure_id?: string; has_certificate?: boolean }
    return d.has_certificate ? `${d.measure_id} (with certificate)` : `${d.measure_id ?? ""}`
  }
  return ""
}

/** Timeline of everything that has happened to this home (spec L13). */
export function EventsTimeline({ events }: { events: PassportEvent[] }) {
  const sorted = [...events].sort((a, b) => b.at.localeCompare(a.at))
  if (sorted.length === 0) return <p className="text-muted-foreground text-sm">Nothing yet.</p>

  return (
    <ol className="space-y-2">
      {sorted.map((e) => (
        <li key={e.id} className="border-border flex items-baseline gap-3 border-l-2 pl-3 text-sm">
          <span className="text-muted-foreground shrink-0">{e.at.slice(0, 10)}</span>
          <span className="font-medium">{KIND_LABEL[e.kind]}</span>
          <span className="text-muted-foreground">{describe(e)}</span>
          {e.score_after !== null && (
            <span className="text-muted-foreground">Score {e.score_after}</span>
          )}
        </li>
      ))}
    </ol>
  )
}
