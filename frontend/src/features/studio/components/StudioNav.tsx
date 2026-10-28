import Link from "next/link"

const CHAPTERS: { id: string; label: string }[] = [
  { id: "understand", label: "Understand" },
  { id: "measure", label: "Measure" },
  { id: "plan", label: "Plan" },
  { id: "live", label: "Live" },
  { id: "money", label: "Money" },
  { id: "ask", label: "Ask" },
]

export function StudioNav({ ref }: { ref: string }) {
  return (
    <nav
      className="s-mono flex flex-wrap gap-4 border-b pb-3"
      style={{ borderColor: "var(--s-stone-200)" }}
    >
      <Link href="/studio" className="s-focus-ring underline">
        Studio
      </Link>
      {CHAPTERS.map((c) => (
        <Link key={c.id} href={`/studio/${ref}#${c.id}`} className="s-focus-ring hover:underline">
          {c.label}
        </Link>
      ))}
    </nav>
  )
}
