import Link from "next/link"

export function SiteHeader() {
  return (
    <header className="bg-deep text-white">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link
          href="/"
          className="rounded-sm font-semibold tracking-tight focus-visible:ring-2 focus-visible:ring-white focus-visible:outline-none"
        >
          Home Resilience Passport
        </Link>
      </div>
    </header>
  )
}
