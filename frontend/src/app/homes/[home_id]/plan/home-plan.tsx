"use client"

import { useEffect, useRef, useState } from "react"

import { RequireUser } from "@/components/auth/require-user"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { Plan } from "@/lib/api/types"
import { usePassport } from "@/lib/journey/use-passport"

export function HomePlan({ homeId }: { homeId: string }) {
  return <RequireUser>{() => <PlanBody homeId={homeId} />}</RequireUser>
}

const DEBOUNCE_MS = 400

function PlanBody({ homeId }: { homeId: string }) {
  const passportState = usePassport(homeId)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [budget, setBudget] = useState(0)
  const [selectedIds, setSelectedIds] = useState<string[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const initialized = useRef(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // First load: no body, so the API uses the household's own budget and default selection.
  useEffect(() => {
    if (passportState.status !== "ready" || initialized.current) return
    initialized.current = true
    setBudget(passportState.passport.household.budget_gbp)
    api
      .POST("/api/v1/homes/{home_id}/plan", { params: { path: { home_id: homeId } }, body: {} })
      .then(unwrap)
      .then((p) => {
        setPlan(p)
        setSelectedIds(p.items.filter((i) => i.selected).map((i) => i.measure.id))
      })
      .catch((e: unknown) => setError(isApiError(e) ? e.detail : "Could not load your plan."))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [passportState.status])

  // Any later change to budget or selection re-posts, debounced (CONTRACT §4.4 timing note).
  useEffect(() => {
    if (!initialized.current || selectedIds === null) return
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      api
        .POST("/api/v1/homes/{home_id}/plan", {
          params: { path: { home_id: homeId } },
          body: { budget_gbp: budget, selected_ids: selectedIds },
        })
        .then(unwrap)
        .then(setPlan)
        .catch((e: unknown) => setError(isApiError(e) ? e.detail : "Could not update your plan."))
    }, DEBOUNCE_MS)
    return () => {
      if (timer.current) clearTimeout(timer.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [budget, selectedIds])

  if (passportState.status === "loading" || !plan || selectedIds === null) {
    return <p className="text-muted-foreground">Loading…</p>
  }
  if (passportState.status === "error") return <p role="alert">{passportState.error.detail}</p>
  if (error) return <p role="alert">{error}</p>

  const isRenter =
    passportState.passport.household.tenure === "private_renter" ||
    passportState.passport.household.tenure === "social_renter"

  const own = plan.items.filter((i) => !isRenter || !i.measure.needs_landlord)
  const landlord = isRenter ? plan.items.filter((i) => i.measure.needs_landlord) : []

  function toggle(id: string) {
    setSelectedIds((ids) =>
      ids!.includes(id) ? ids!.filter((x) => x !== id) : [...ids!, id],
    )
  }

  return (
    <div className="space-y-8">
      <div className="bg-mint grid grid-cols-2 gap-4 rounded-lg p-4 sm:grid-cols-4">
        <Total label="Cost">
          £{plan.total_cost_low_gbp.toLocaleString()} - £{plan.total_cost_high_gbp.toLocaleString()}
        </Total>
        <Total label="Projected score">
          {plan.projected_score.value} ({plan.projected_score.band})
        </Total>
        <Total label="Measures selected">{selectedIds.length}</Total>
        <Total label="Budget">£{budget.toLocaleString()}</Total>
      </div>

      <div className="space-y-2">
        <label htmlFor="budget" className="block text-sm font-medium">
          Your budget: £{budget.toLocaleString()}
        </label>
        <input
          id="budget"
          type="range"
          min={0}
          max={30000}
          step={250}
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
          className="w-full max-w-md"
        />
      </div>

      <PlanGroup title="Your plan" items={own} selectedIds={selectedIds} onToggle={toggle} />
      {isRenter && landlord.length > 0 && (
        <PlanGroup
          title="Ask your landlord"
          items={landlord}
          selectedIds={selectedIds}
          onToggle={toggle}
        />
      )}

      <a
        href={`/homes/${homeId}/funding`}
        className="text-deep inline-block text-sm underline underline-offset-4"
      >
        See your funding options →
      </a>
    </div>
  )
}

function Total({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="text-deep font-semibold">{children}</p>
    </div>
  )
}

function PlanGroup({
  title,
  items,
  selectedIds,
  onToggle,
}: {
  title: string
  items: Plan["items"]
  selectedIds: string[]
  onToggle: (id: string) => void
}) {
  const sorted = [...items].sort((a, b) => a.rank - b.rank)
  if (sorted.length === 0) return null
  return (
    <div className="space-y-3">
      <h2 className="font-semibold">{title}</h2>
      <ul className="space-y-3">
        {sorted.map((item) => (
          <li key={item.measure.id} className="border-border rounded-lg border p-4">
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={selectedIds.includes(item.measure.id)}
                onChange={() => onToggle(item.measure.id)}
                className="mt-1"
              />
              <div className="space-y-1">
                <p className="font-medium">{item.measure.name}</p>
                <p className="text-muted-foreground text-sm">
                  £{item.measure.cost_low_gbp.toLocaleString()} - £
                  {item.measure.cost_high_gbp.toLocaleString()} · Saves £
                  {item.measure.annual_bill_saving_gbp.toLocaleString()}/yr · Saves{" "}
                  {item.measure.co2_saved_kg_per_year.toLocaleString()} kg CO₂/yr · +
                  {item.score_uplift.toFixed(1)} score
                </p>
                <p className="text-sm">{item.explanation}</p>
              </div>
            </label>
          </li>
        ))}
      </ul>
    </div>
  )
}
