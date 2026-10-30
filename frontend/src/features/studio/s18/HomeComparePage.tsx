"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer } from "recharts"

import { api, unwrap } from "@/lib/api/client"
import type { DemoHome, LookupAddress } from "@/lib/api/types"
import { loginPath, useUser } from "@/lib/auth/use-user"

import { studioApi, unwrap as studioUnwrap } from "@/features/studio/api/client"
import type { Compare, CompareHome } from "@/features/studio/api/types"
import { ErrorState } from "@/features/studio/components/ErrorState"
import { FallbackChip } from "@/features/studio/components/FallbackChip"
import { ragColor } from "@/features/studio/lib/rag"

const MIN_ROWS = 2
const MAX_ROWS = 3

const HAZARD_LABEL: Record<string, string> = {
  river_sea_flood: "River & sea flood",
  overheating: "Overheating",
  storm: "Storm",
  subsidence: "Subsidence",
  surface_water: "Surface water",
}

const COMPONENT_LABEL: Record<string, string> = {
  flood: "Flood",
  heat: "Heat",
  storm: "Storm",
  subsidence: "Subsidence",
  carbon: "Carbon",
}

const SERIES_COLOUR: Record<string, string> = {
  A: "var(--s-green-700, #1e5631)",
  B: "var(--s-brass-500, #b08d57)",
  C: "var(--s-blue-600, #2a5f8f)",
}

type Row = {
  postcode: string
  line1: string
  uprn: string | null
  addresses: LookupAddress[] | null
  looking_up: boolean
  lookupError: string | null
}

function emptyRow(): Row {
  return {
    postcode: "",
    line1: "",
    uprn: null,
    addresses: null,
    looking_up: false,
    lookupError: null,
  }
}

function costRange(low: number | null, high: number | null): string {
  if (low === null || high === null) return "Not reachable with the available measures"
  return `£${low.toLocaleString()}–£${high.toLocaleString()}`
}

export function HomeComparePage() {
  const { status } = useUser()
  const [rows, setRows] = useState<Row[]>([emptyRow(), emptyRow()])
  const [demos, setDemos] = useState<DemoHome[] | null>(null)
  const [selectedDemos, setSelectedDemos] = useState<string[]>([])
  const [result, setResult] = useState<Compare | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.GET("/api/v1/demo/homes").then(unwrap).then(setDemos).catch(setError)
  }, [])

  function updateRow(i: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))
  }

  async function lookup(i: number) {
    const row = rows[i]
    if (!row.postcode.trim()) return
    updateRow(i, { looking_up: true, lookupError: null, addresses: null })
    try {
      const info = unwrap(
        await api.GET("/api/v1/lookup/postcode/{postcode}", {
          params: { path: { postcode: row.postcode } },
        }),
      )
      updateRow(i, { looking_up: false, addresses: info.addresses })
    } catch {
      updateRow(i, { looking_up: false, lookupError: "We couldn't look up that postcode." })
    }
  }

  function pickAddress(i: number, addr: LookupAddress) {
    updateRow(i, { line1: addr.line1, uprn: addr.uprn })
  }

  function addRow() {
    if (rows.length < MAX_ROWS) setRows((prev) => [...prev, emptyRow()])
  }

  function removeRow(i: number) {
    if (rows.length > MIN_ROWS) setRows((prev) => prev.filter((_, idx) => idx !== i))
  }

  function toggleDemo(slug: string) {
    setSelectedDemos((prev) =>
      prev.includes(slug)
        ? prev.filter((s) => s !== slug)
        : prev.length < MAX_ROWS
          ? [...prev, slug]
          : prev,
    )
  }

  async function submitCompare() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const candidates = rows.map((r) => ({ postcode: r.postcode, line1: r.line1, uprn: r.uprn }))
      const body = studioUnwrap(
        await studioApi.POST("/api/v1/studio/compare", { body: { candidates } }),
      )
      setResult(body)
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }

  async function submitDemoCompare() {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const body = studioUnwrap(
        await studioApi.GET("/api/v1/studio/compare/demo", {
          params: { query: { slugs: selectedDemos.join(",") } },
        }),
      )
      setResult(body)
    } catch (e) {
      setError(e)
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = rows.every((r) => r.postcode.trim() && r.line1.trim())
  const canSubmitDemo = selectedDemos.length >= MIN_ROWS

  return (
    <div className="space-y-10">
      <section className="s-stage s-reveal rounded-3xl p-10" style={{ color: "var(--s-paper)" }}>
        <p className="s-eyebrow">S18 · Home Compare</p>
        <h1 className="s-display mt-2 text-4xl" style={{ color: "var(--s-paper)" }}>
          Thinking of buying? Compare resilience side by side.
        </h1>
        <p className="mt-3 max-w-xl" style={{ color: "var(--s-paper)" }}>
          Nothing here is saved. We run the same checks used for a passport, read-only, on addresses
          you choose.
        </p>
      </section>

      <section className="s-card space-y-4">
        <h2 className="s-display text-lg">Enter two or three addresses</h2>
        {status === "anonymous" ? (
          <p className="text-sm" style={{ color: "var(--s-stone-500)" }}>
            <Link href={loginPath("/studio/compare")} className="underline">
              Sign in
            </Link>{" "}
            to compare real addresses, or try it with demo homes below.
          </p>
        ) : null}
        {rows.map((row, i) => (
          <div
            key={i}
            className="space-y-2 rounded-xl border p-3"
            style={{ borderColor: "var(--s-stone-200)" }}
          >
            <div className="flex items-end gap-2">
              <label className="flex-1 text-sm">
                Postcode
                <input
                  className="s-focus-ring mt-1 block w-full rounded border px-2 py-1"
                  style={{ borderColor: "var(--s-stone-200)" }}
                  value={row.postcode}
                  onChange={(e) => updateRow(i, { postcode: e.target.value })}
                  placeholder="SW1A 1AA"
                />
              </label>
              <button
                type="button"
                className="s-focus-ring rounded px-3 py-1 text-sm"
                style={{ background: "var(--s-green-100)", color: "var(--s-green-700)" }}
                onClick={() => lookup(i)}
                disabled={row.looking_up}
              >
                {row.looking_up ? "Looking up…" : "Find address"}
              </button>
              {rows.length > MIN_ROWS ? (
                <button
                  type="button"
                  className="s-focus-ring rounded px-2 py-1 text-sm"
                  onClick={() => removeRow(i)}
                  aria-label="Remove this home"
                >
                  Remove
                </button>
              ) : null}
            </div>
            {row.lookupError ? (
              <p className="text-sm" style={{ color: "var(--s-risk-high)" }}>
                {row.lookupError}
              </p>
            ) : null}
            {row.addresses && row.addresses.length > 0 ? (
              <select
                className="s-focus-ring block w-full rounded border px-2 py-1 text-sm"
                style={{ borderColor: "var(--s-stone-200)" }}
                onChange={(e) => {
                  const addr = row.addresses?.find((a) => a.line1 === e.target.value)
                  if (addr) pickAddress(i, addr)
                }}
                value={row.line1}
              >
                <option value="">Choose the address…</option>
                {row.addresses.map((a) => (
                  <option key={a.line1} value={a.line1}>
                    {a.line1}
                  </option>
                ))}
              </select>
            ) : (
              <label className="block text-sm">
                Address line 1
                <input
                  className="s-focus-ring mt-1 block w-full rounded border px-2 py-1"
                  style={{ borderColor: "var(--s-stone-200)" }}
                  value={row.line1}
                  onChange={(e) => updateRow(i, { line1: e.target.value, uprn: null })}
                  placeholder="1 Example Street"
                />
              </label>
            )}
          </div>
        ))}
        <div className="flex items-center justify-between">
          {rows.length < MAX_ROWS ? (
            <button type="button" className="s-focus-ring text-sm underline" onClick={addRow}>
              Add a third home
            </button>
          ) : (
            <span />
          )}
          <button
            type="button"
            className="s-focus-ring rounded-full px-4 py-2 text-sm font-medium"
            style={{ background: "var(--s-green-700)", color: "var(--s-paper)" }}
            onClick={submitCompare}
            disabled={!canSubmit || loading || status !== "authenticated"}
          >
            {loading ? "Comparing…" : "Compare"}
          </button>
        </div>
      </section>

      <section className="s-card space-y-3">
        <h2 className="s-display text-lg">Or try it with demo homes</h2>
        {!demos ? (
          <p className="text-sm" style={{ color: "var(--s-stone-500)" }}>
            Loading demo homes…
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {demos.map((d) => (
              <li key={d.slug}>
                <label
                  className="s-focus-ring flex items-center gap-2 rounded-full border px-3 py-1 text-sm"
                  style={{ borderColor: "var(--s-stone-200)" }}
                >
                  <input
                    type="checkbox"
                    checked={selectedDemos.includes(d.slug)}
                    onChange={() => toggleDemo(d.slug)}
                  />
                  {d.address.line1}
                </label>
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="s-focus-ring rounded-full px-4 py-2 text-sm font-medium"
          style={{ background: "var(--s-green-100)", color: "var(--s-green-700)" }}
          onClick={submitDemoCompare}
          disabled={!canSubmitDemo || loading}
        >
          {loading ? "Comparing…" : `Compare ${selectedDemos.length || ""} demo homes`}
        </button>
      </section>

      {error ? <ErrorState error={error} /> : null}

      {result ? <CompareResult result={result} /> : null}
    </div>
  )
}

function CompareResult({ result }: { result: Compare }) {
  const components = Object.keys(COMPONENT_LABEL)
  const radarData = components.map((name) => {
    const row: Record<string, string | number> = { component: COMPONENT_LABEL[name] }
    for (const home of result.homes) {
      const c = home.score.components.find((c) => c.name === name)
      row[home.label] = c ? c.points : 0
    }
    return row
  })

  return (
    <section className="space-y-6">
      {result.fallback_used ? <FallbackChip /> : null}

      <div className="s-card">
        <p className="s-display text-lg">{result.summary}</p>
      </div>

      <div className="h-80 w-full">
        <ResponsiveContainer>
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis dataKey="component" />
            {result.homes.map((home) => (
              <Radar
                key={home.label}
                name={`Home ${home.label}`}
                dataKey={home.label}
                stroke={SERIES_COLOUR[home.label]}
                fill={SERIES_COLOUR[home.label]}
                fillOpacity={0.15}
              />
            ))}
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {result.homes.map((home) => (
          <HomeCard key={home.label} home={home} winners={result.winners} />
        ))}
      </div>
    </section>
  )
}

function HomeCard({ home, winners }: { home: CompareHome; winners: Compare["winners"] }) {
  const isOverallWinner = winners.overall === home.label
  return (
    <div className="s-card space-y-3">
      <div className="flex items-center justify-between">
        <p className="s-eyebrow">
          Home {home.label}
          {isOverallWinner ? " 👑" : ""}
        </p>
        <p className="s-mono text-sm" style={{ color: "var(--s-stone-500)" }}>
          {home.property.epc_rating ?? "No EPC"}
        </p>
      </div>
      <p className="font-medium">{home.line1}</p>
      <p className="text-sm" style={{ color: "var(--s-stone-500)" }}>
        {home.postcode}
      </p>
      <p className="s-display text-3xl">
        {home.score.value}
        <span className="ml-1 text-base" style={{ color: "var(--s-stone-500)" }}>
          /100 · band {home.score.band}
        </span>
      </p>

      <table className="w-full text-sm">
        <tbody>
          {home.risk.levels.map((level) => (
            <tr key={level.hazard}>
              <td className="py-0.5">{HAZARD_LABEL[level.hazard] ?? level.hazard}</td>
              <td className="py-0.5 text-right" style={{ color: ragColor(level.today) }}>
                {level.today}
              </td>
              <td className="py-0.5 text-right" style={{ color: ragColor(level.y2050) }}>
                → {level.y2050}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div>
        <p className="s-eyebrow">Cost to reach a 70 score</p>
        <p className="text-sm">{costRange(home.cost_to_70_low_gbp, home.cost_to_70_high_gbp)}</p>
      </div>

      {home.top_measures.length > 0 ? (
        <div>
          <p className="s-eyebrow">Top measures</p>
          <ul className="mt-1 space-y-1 text-sm">
            {home.top_measures.map((m) => (
              <li key={m.measure_id}>
                {m.name} · £{m.cost_low_gbp.toLocaleString()}–£{m.cost_high_gbp.toLocaleString()} ·
                +{m.score_uplift} pts
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {(["flood", "heat", "storm", "subsidence", "carbon"] as const).map((c) =>
        winners[c] === home.label ? (
          <span
            key={c}
            className="s-mono mr-1 inline-block rounded-full px-2 py-0.5 text-xs"
            style={{ background: "var(--s-green-100)", color: "var(--s-green-700)" }}
          >
            Best {COMPONENT_LABEL[c]}
          </span>
        ) : null,
      )}
    </div>
  )
}
