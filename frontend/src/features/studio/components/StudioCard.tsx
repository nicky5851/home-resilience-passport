export function StudioCard({
  children,
  className = "",
}: {
  children: React.ReactNode
  className?: string
}) {
  return <div className={`s-card ${className}`}>{children}</div>
}
