import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function Home() {
  return (
    <section className="space-y-4">
      <h1 className="text-deep text-3xl font-semibold tracking-tight">
        How ready is your home for the climate of 2050?
      </h1>
      <p className="text-muted-foreground max-w-2xl text-lg">
        Enter your postcode to see your flood, heat, storm and subsidence risks, your Resilience
        Score, and a costed plan with the funding you qualify for.
      </p>
      <div className="flex gap-3 pt-2">
        <Button asChild>
          <Link href="/start">Start</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/start">Try a demo home</Link>
        </Button>
      </div>
    </section>
  )
}
