export function SkeletonBlock({ height = 120 }: { height?: number }) {
  return (
    <div
      aria-hidden="true"
      className="animate-pulse rounded-2xl"
      style={{ height, background: "var(--s-green-100)" }}
    />
  )
}
