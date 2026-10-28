export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <div className="s-card text-center" style={{ color: "var(--s-stone-500)" }}>
      <p className="font-medium" style={{ color: "var(--s-ink)" }}>
        {title}
      </p>
      {body ? <p className="mt-1 text-sm">{body}</p> : null}
    </div>
  )
}
