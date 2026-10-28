"use client"

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import type { PassportEvent } from "@/lib/api/types"

/** Score-over-time chart from the events that recorded a new score (spec L13). */
export function ScoreHistory({ events }: { events: PassportEvent[] }) {
  const points = events
    .filter((e) => e.score_after !== null)
    .sort((a, b) => a.at.localeCompare(b.at))
    .map((e) => ({ date: e.at.slice(0, 10), score: e.score_after as number }))

  if (points.length === 0) {
    return <p className="text-muted-foreground text-sm">No score history yet.</p>
  }

  return (
    <LineChart width={480} height={200} data={points} margin={{ left: 0, right: 16 }}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="date" fontSize={12} />
      <YAxis domain={[0, 100]} fontSize={12} width={32} />
      <Line type="monotone" dataKey="score" stroke="var(--color-green)" strokeWidth={2} dot />
    </LineChart>
  )
}
