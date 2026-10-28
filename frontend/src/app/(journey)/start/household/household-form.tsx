"use client"

import { zodResolver } from "@hookform/resolvers/zod"
import { useRouter } from "next/navigation"
import { useEffect, useRef, useState } from "react"
import { Controller, useForm } from "react-hook-form"
import { z } from "zod"

import { Button } from "@/components/ui/button"
import { isApiError } from "@/lib/api/errors"
import type { HouseholdInput } from "@/lib/api/types"
import { loginPath, useUser } from "@/lib/auth/use-user"
import { clearDraft, loadDraft, saveDraft } from "@/lib/journey/draft"
import { createAndAssessHome } from "@/lib/journey/create-home"

const TENURES: [HouseholdInput["tenure"], string][] = [
  ["owner_occupier", "I own and live in it"],
  ["landlord", "I own it and rent it out"],
  ["private_renter", "I rent privately"],
  ["social_renter", "I rent from a council or housing association"],
]

const INCOME_BANDS: [HouseholdInput["income_band"], string][] = [
  ["under_20k", "Under £20,000"],
  ["20k_40k", "£20,000 - £40,000"],
  ["40k_60k", "£40,000 - £60,000"],
  ["60k_100k", "£60,000 - £100,000"],
  ["over_100k", "Over £100,000"],
]

const PRIORITIES: [NonNullable<HouseholdInput["priorities"]>[number], string][] = [
  ["lower_bills", "Lower energy bills"],
  ["comfort", "Comfort (not too hot, not too cold)"],
  ["flood_safety", "Flood safety"],
  ["lower_carbon", "Lower carbon footprint"],
  ["home_value", "Home value"],
]

const VULNERABLE_TEXT =
  "Optional. If someone in your home is over 75, disabled, has a long-term illness or young " +
  "children, tell us and we will put safety measures first. We only use this to order your plan " +
  "and you can remove it any time."

const schema = z.object({
  tenure: z.enum(["owner_occupier", "landlord", "private_renter", "social_renter"], {
    message: "Select how you hold this home.",
  }),
  income_band: z.enum(["under_20k", "20k_40k", "40k_60k", "60k_100k", "over_100k"], {
    message: "Select your household income band.",
  }),
  budget_gbp: z
    .number({ message: "Enter a budget in pounds." })
    .int("Enter a whole number of pounds.")
    .min(0, "Enter a budget of £0 or more."),
  priorities: z.array(
    z.enum(["lower_bills", "comfort", "flood_safety", "lower_carbon", "home_value"]),
  ),
  vulnerable: z.boolean().nullable(),
  consent_lloyds_data: z.boolean(),
})

type FormValues = z.infer<typeof schema>

const DEFAULT_VALUES: FormValues = {
  tenure: "owner_occupier",
  income_band: "40k_60k",
  budget_gbp: 5000,
  priorities: [],
  vulnerable: null,
  consent_lloyds_data: false,
}

const PROGRESS_STEPS = ["Checking flood maps…", "Climate projections…", "Energy certificate…"]

/** Household form (spec L8); mirrors `Household-Input` with react-hook-form + zod. */
export function HouseholdForm() {
  const router = useRouter()
  const user = useUser()
  const autoSubmitted = useRef(false)
  const [progress, setProgress] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULT_VALUES,
  })

  useEffect(() => {
    const draft = loadDraft()
    if (!draft?.address) {
      router.replace("/start")
      return
    }
    if (draft.household) reset({ ...DEFAULT_VALUES, ...draft.household })
  }, [reset, router])

  async function submit(values: FormValues) {
    const draft = loadDraft()
    if (!draft?.address) {
      router.replace("/start")
      return
    }
    if (user.status !== "authenticated") {
      saveDraft({ ...draft, household: values })
      router.push(loginPath("/start/household"))
      return
    }
    setSubmitError(null)
    let i = 0
    setProgress(PROGRESS_STEPS[0]!)
    const timer = setInterval(() => {
      i = (i + 1) % PROGRESS_STEPS.length
      setProgress(PROGRESS_STEPS[i]!)
    }, 1500)
    try {
      const homeId = await createAndAssessHome(draft.address, values, draft.property)
      clearDraft()
      router.push(`/homes/${homeId}/risk`)
    } catch (e) {
      setSubmitError(isApiError(e) ? e.detail : "Something went wrong. Please try again.")
    } finally {
      clearInterval(timer)
      setProgress(null)
    }
  }

  // After the forced login round trip, the household answers are already filled in — pick up
  // where the user left off instead of asking them to submit twice (CONTRACT §4.4).
  useEffect(() => {
    if (user.status !== "authenticated" || autoSubmitted.current) return
    const draft = loadDraft()
    if (!draft?.household) return
    autoSubmitted.current = true
    void handleSubmit(submit)()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user.status])

  if (progress) {
    return (
      <p role="status" aria-live="polite" className="text-deep">
        {progress}
      </p>
    )
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-6" noValidate>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">How do you hold this home?</legend>
        {TENURES.map(([value, label]) => (
          <label key={value} className="flex items-center gap-2 text-sm">
            <input type="radio" value={value} {...register("tenure")} />
            {label}
          </label>
        ))}
        {errors.tenure && (
          <p role="alert" className="text-risk text-sm">
            {errors.tenure.message}
          </p>
        )}
      </fieldset>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Household income</legend>
        {INCOME_BANDS.map(([value, label]) => (
          <label key={value} className="flex items-center gap-2 text-sm">
            <input type="radio" value={value} {...register("income_band")} />
            {label}
          </label>
        ))}
        {errors.income_band && (
          <p role="alert" className="text-risk text-sm">
            {errors.income_band.message}
          </p>
        )}
      </fieldset>

      <div className="space-y-1">
        <label htmlFor="budget_gbp" className="block text-sm font-medium">
          Budget for improvements (£)
        </label>
        <input
          id="budget_gbp"
          type="number"
          min={0}
          step={100}
          inputMode="numeric"
          className="border-input w-full max-w-xs rounded-md border px-3 py-2"
          {...register("budget_gbp", { valueAsNumber: true })}
        />
        {errors.budget_gbp && (
          <p role="alert" className="text-risk text-sm">
            {errors.budget_gbp.message}
          </p>
        )}
      </div>

      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">What matters most to you? (optional)</legend>
        <Controller
          control={control}
          name="priorities"
          render={({ field }) => (
            <>
              {PRIORITIES.map(([value, label]) => (
                <label key={value} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={field.value.includes(value)}
                    onChange={(e) =>
                      field.onChange(
                        e.target.checked
                          ? [...field.value, value]
                          : field.value.filter((v) => v !== value),
                      )
                    }
                  />
                  {label}
                </label>
              ))}
            </>
          )}
        />
      </fieldset>

      <fieldset className="border-border bg-mint space-y-2 rounded-md border p-3">
        <legend className="sr-only">Vulnerability (optional)</legend>
        <p className="text-sm">{VULNERABLE_TEXT}</p>
        <Controller
          control={control}
          name="vulnerable"
          render={({ field }) => (
            <div className="flex gap-4 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={field.value === true}
                  onChange={() => field.onChange(true)}
                />
                Yes
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={field.value === false}
                  onChange={() => field.onChange(false)}
                />
                No
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={field.value === null}
                  onChange={() => field.onChange(null)}
                />
                Prefer not to say
              </label>
            </div>
          )}
        />
      </fieldset>

      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" {...register("consent_lloyds_data")} />
        <span>
          I would like to be matched against Lloyds Banking Group funding products using the answers
          above (optional).
        </span>
      </label>

      {submitError && (
        <p role="alert" className="text-risk text-sm">
          {submitError}
        </p>
      )}

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Continuing…" : "Continue"}
      </Button>
    </form>
  )
}
