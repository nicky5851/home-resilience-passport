import Link from "next/link"

export const ATTRIBUTION =
  "Contains public sector information licensed under the Open Government Licence v3.0. Climate data: Open-Meteo, CMIP6."

export function SiteFooter() {
  return (
    <footer className="border-border bg-mint text-muted-foreground border-t">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 px-4 py-6 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p>{ATTRIBUTION}</p>
        <Link href="/privacy" className="text-deep shrink-0 underline underline-offset-4">
          Privacy
        </Link>
      </div>
    </footer>
  )
}
