"use client"

import { useEffect, useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { Portfolio, ScenarioResult } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { StatTile } from "@/features/studio/components/StatTile"

const LEVEL_COLOUR: Record<string, string> = {
  low: "var(--s-green-500, #4a9d6e)",
  medium: "var(--s-brass-500, #b08d57)",
  high: "var(--s-red-600, #b3261e)",
}

const BAND_COLOUR: Record<string, string> = {
  A: "#00a651",
  B: "#19b459",
  C: "#8dc63f",
  D: "#fff200",
  E: "#fbb040",
  F: "#f36f21",
  G: "#ed1c24",
}

const YEARS = [2026, 2028, 2030, 2032, 2035]

export function LenderPortfolioLensPage() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [uptake, setUptake] = useState(25)
  const [year, setYear] = useState(2030)
  const [scenario, setScenario] = useState<ScenarioResult | null>(null)
  const [scenarioLoading, setScenarioLoading] = useState(false)

  useEffect(() => {
    studioApi.GET("/api/v1/studio/portfolio").then(unwrap).then(setPortfolio).catch(setError)
  }, [])

  useEffect(() => {
    setScenarioLoading(true)
    studioApi
      .POST("/api/v1/studio/portfolio/scenario", { body: { uptake_pct: uptake, by_year: year } })
      .then(unwrap)
      .then(setScenario)
      .catch(setError)
      .finally(() => setScenarioLoading(false))
  }, [uptake, year])

  if (error) return <ErrorState error={error} />
  if (!portfolio) return <p className="s-mono">Loading the portfolio sample…</p>

  return (
    <div className="space-y-10">
      <section className="s-stage s-reveal rounded-3xl p-10" style={{ color: "var(--s-paper)" }}>
        <p className="s-eyebrow">
          S20 · Lender Portfolio Lens · Illustrative · {portfolio.sample_size} public EPC records
        </p>
        <h1 className="s-display mt-2 text-4xl" style={{ color: "var(--s-paper)" }}>
          A lender&apos;s view of climate exposure and retrofit opportunity.
        </h1>
        <p className="mt-3 max-w-2xl" style={{ color: "var(--s-paper)" }}>
          {portfolio.sample_note}
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile eyebrow="Below EPC C" value={`${portfolio.below_c_share_pct}%`} />
        <StatTile
          eyebrow="Transition finance opportunity"
          value={`£${portfolio.transition_cost_low_gbp.toLocaleString()}–£${portfolio.transition_cost_high_gbp.toLocaleString()}`}
        />
        <StatTile
          eyebrow="Financed emissions"
          value={`${portfolio.financed_emissions_t}`}
          unit="t CO₂/yr"
        />
        <StatTile eyebrow="Sample generated" value={portfolio.generated_on} />
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="s-card">
          <p className="s-eyebrow">EPC band distribution</p>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={portfolio.by_epc_band}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="band" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count">
                  {portfolio.by_epc_band.map((b) => (
                    <Cell key={b.band} fill={BAND_COLOUR[b.band] ?? "#D1D5DB"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="s-card">
          <p className="s-eyebrow">Resilience score band</p>
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={portfolio.by_score_band}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="band" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="var(--s-green-700)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="s-card">
          <p className="s-eyebrow">Flood exposure by 2050</p>
          <div className="h-56">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={portfolio.flood_exposure} dataKey="count" nameKey="level" label>
                  {portfolio.flood_exposure.map((l) => (
                    <Cell key={l.level} fill={LEVEL_COLOUR[l.level]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="s-card">
          <p className="s-eyebrow">Overheating risk by 2050</p>
          <div className="h-56">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={portfolio.heat_2050} dataKey="count" nameKey="level" label>
                  {portfolio.heat_2050.map((l) => (
                    <Cell key={l.level} fill={LEVEL_COLOUR[l.level]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="s-card">
        <p className="s-eyebrow">Districts (postcode outward codes with 5+ homes)</p>
        <div className="mt-2 max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left" style={{ color: "var(--s-stone-500)" }}>
                <th className="py-1">District</th>
                <th className="py-1 text-right">Homes</th>
                <th className="py-1 text-right">Avg score</th>
                <th className="py-1 text-right">Below C</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.districts
                .slice()
                .sort((a, b) => b.count - a.count)
                .map((d) => (
                  <tr key={d.outcode}>
                    <td className="s-mono py-0.5">{d.outcode}</td>
                    <td className="py-0.5 text-right">{d.count}</td>
                    <td className="py-0.5 text-right">{d.avg_score}</td>
                    <td className="py-0.5 text-right">{d.below_c_share_pct}%</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs" style={{ color: "var(--s-stone-500)" }}>
          Shown as a sortable table rather than a map: we don&apos;t have precise district-level
          coordinates for every outward code offline.
        </p>
      </section>

      <section className="s-card space-y-4">
        <p className="s-eyebrow">Scenario: what if D-G homes take up their plan?</p>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          <label className="flex-1 text-sm">
            Uptake: {uptake}%
            <input
              type="range"
              min={0}
              max={100}
              value={uptake}
              onChange={(e) => setUptake(Number(e.target.value))}
              className="s-focus-ring mt-1 block w-full"
            />
          </label>
          <div className="flex gap-1">
            {YEARS.map((y) => (
              <button
                key={y}
                type="button"
                className="s-focus-ring rounded-full px-3 py-1 text-sm"
                style={{
                  background: y === year ? "var(--s-green-700)" : "var(--s-green-100)",
                  color: y === year ? "var(--s-paper)" : "var(--s-green-700)",
                }}
                onClick={() => setYear(y)}
              >
                {y}
              </button>
            ))}
          </div>
        </div>

        {scenario ? (
          <>
            <div className="h-48">
              <ResponsiveContainer>
                <BarChart
                  data={[
                    { label: "Before", emissions: scenario.emissions_before_t },
                    { label: "After", emissions: scenario.emissions_after_t },
                  ]}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="emissions" fill="var(--s-green-700)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className={scenarioLoading ? "opacity-50" : ""}>
              If {uptake}% of D-G homes take up their plan by {year}, financed emissions fall{" "}
              {scenario.reduction_pct}% and {scenario.homes_upgraded} homes are upgraded, needing £
              {scenario.finance_needed_low_gbp.toLocaleString()}–£
              {scenario.finance_needed_high_gbp.toLocaleString()} of transition finance. The share
              below EPC C falls to {scenario.below_c_share_after_pct}%.
            </p>
          </>
        ) : null}
      </section>

      <section className="s-card">
        <p className="s-eyebrow">Fairness</p>
        <p className="mt-1">{portfolio.fairness_note}</p>
        <p className="mt-2 text-sm" style={{ color: "var(--s-stone-500)" }}>
          {portfolio.attribution_note}
        </p>
      </section>
    </div>
  )
}
