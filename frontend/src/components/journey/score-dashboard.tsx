"use client"

import { PolarAngleAxis, RadialBar, RadialBarChart } from "recharts"

import type { PropertyFacts, ResilienceScore } from "@/lib/api/types"

const COMPONENT_LABEL: Record<ResilienceScore["components"][number]["name"], string> = {
  flood: "Flood",
  heat: "Heat",
  storm: "Storm",
  subsidence: "Subsidence",
  carbon: "Carbon",
}

const BAND_EXPLAINER: Record<ResilienceScore["band"], string> = {
  A: "Excellent. This home is well prepared for the climate of 2050.",
  B: "Good. This home is in good shape, with some room to improve.",
  C: "Fair. A few improvements would make a real difference.",
  D: "Below average. Several risks are not well managed yet.",
  E: "Poor. This home faces real climate risks without much protection.",
  F: "Very poor. Significant work is needed to protect this home.",
  G: "Critical. This home is highly exposed with little resilience in place.",
}

function bandColor(band: ResilienceScore["band"]): string {
  if (band === "A" || band === "B") return "var(--color-level-low)"
  if (band === "C" || band === "D") return "var(--color-level-medium)"
  return "var(--color-level-high)"
}

/** Resilience score dashboard (spec L10): radial gauge, component bars, EPC, explainer. */
export function ScoreDashboard({
  score,
  property,
}: {
  score: ResilienceScore
  property: PropertyFacts
}) {
  const color = bandColor(score.band)
  const gaugeData = [{ name: "score", value: score.value, fill: color }]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-8">
        <div className="relative size-48 shrink-0">
          <RadialBarChart
            width={192}
            height={192}
            cx="50%"
            cy="50%"
            innerRadius="75%"
            outerRadius="100%"
            barSize={16}
            data={gaugeData}
            startAngle={90}
            endAngle={-270}
          >
            <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
            <RadialBar dataKey="value" cornerRadius={8} background />
          </RadialBarChart>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-deep text-4xl font-bold">{score.value}</span>
            <span className="text-muted-foreground text-sm">out of 100</span>
          </div>
          <p role="status" className="sr-only">
            Resilience score {score.value} out of 100, band {score.band}:{" "}
            {BAND_EXPLAINER[score.band]}
          </p>
        </div>

        <div className="space-y-1">
          <p className="text-muted-foreground text-sm">Resilience band</p>
          <p className="text-deep text-3xl font-semibold">{score.band}</p>
          {property.epc_rating && (
            <p className="text-muted-foreground text-sm">EPC rating: {property.epc_rating}</p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {score.components.map((c) => (
          <div key={c.name} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{COMPONENT_LABEL[c.name]}</span>
              <span className="text-muted-foreground">
                {c.points.toFixed(1)} / {c.max_points}
              </span>
            </div>
            <div className="bg-mint h-2 rounded-full">
              <div
                className="bg-green h-2 rounded-full"
                style={{ width: `${Math.min(100, (c.points / c.max_points) * 100)}%` }}
              />
            </div>
            <p className="text-muted-foreground text-sm">{c.reason}</p>
          </div>
        ))}
      </div>

      <details className="border-border rounded-md border p-3">
        <summary className="cursor-pointer font-medium">What does this mean?</summary>
        <p className="text-muted-foreground mt-2 text-sm">{BAND_EXPLAINER[score.band]}</p>
        <p className="text-muted-foreground mt-2 text-sm">
          Your score is out of 100: 30 points for flood risk, 20 for heat, 10 for storm, 10 for
          subsidence, and 30 for your home&apos;s carbon footprint. Completing measures from your
          plan raises the relevant points.
        </p>
      </details>
    </div>
  )
}
