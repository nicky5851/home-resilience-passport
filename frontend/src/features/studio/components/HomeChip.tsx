export function HomeChip(props: {
  line1: string | null
  postcodeDistrict: string | null
  isDemo: boolean
}) {
  const label = props.isDemo
    ? (props.line1 ?? "Demo home")
    : [props.line1, props.postcodeDistrict].filter(Boolean).join(", ")
  return (
    <span
      className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm"
      style={{ background: "var(--s-green-100)", color: "var(--s-green-700)" }}
    >
      <span aria-hidden="true">⌂</span>
      {label}
    </span>
  )
}
