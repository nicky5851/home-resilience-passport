"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type {
  AddressInput,
  LookupAddress,
  PostcodeLookup,
  PropertyFactsInput,
} from "@/lib/api/types"
import { saveDraft } from "@/lib/journey/draft"
import { guessCountry, isPlausiblePostcode, normalisePostcode } from "@/lib/journey/postcode"

const PROPERTY_TYPES: PropertyFactsInput["property_type"][] = [
  "detached",
  "semi_detached",
  "terraced",
  "flat",
  "bungalow",
  "other",
]

const EPC_RATINGS = ["A", "B", "C", "D", "E", "F", "G"] as const

type Step =
  | { kind: "postcode" }
  | { kind: "addresses"; lookup: PostcodeLookup }
  | { kind: "manual"; lookup: PostcodeLookup }

/** Postcode → address list → manual fallback, per L7 (spec §10, CONTRACT §1 rule 9, §3). */
export function StartForm() {
  const router = useRouter()
  const [step, setStep] = useState<Step>({ kind: "postcode" })
  const [postcode, setPostcode] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onLookup(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const normalised = normalisePostcode(postcode)
    if (!normalised) {
      setError("Enter a full UK postcode, for example SW1A 1AA.")
      return
    }
    setBusy(true)
    setError(null)
    try {
      const lookup = unwrap(
        await api.GET("/api/v1/lookup/postcode/{postcode}", {
          params: { path: { postcode: normalised } },
        }),
      )
      setStep({ kind: "addresses", lookup })
    } catch (e) {
      setError(isApiError(e) ? e.detail : "Something went wrong. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  function goToHousehold(address: AddressInput, property?: PropertyFactsInput | null) {
    saveDraft({ address, property })
    router.push("/start/household")
  }

  function chooseAddress(lookup: PostcodeLookup, found: LookupAddress) {
    const address: AddressInput = {
      line1: found.line1,
      postcode: lookup.postcode,
      lat: lookup.lat,
      lon: lookup.lon,
      local_authority: lookup.local_authority,
      country: guessCountry(lookup.postcode),
      uprn: found.uprn,
    }
    const property: PropertyFactsInput | null = found.epc_rating
      ? {
          property_type: "other",
          source: "epc_api",
          epc_rating: found.epc_rating,
        }
      : null
    goToHousehold(address, property)
  }

  if (step.kind === "postcode") {
    return (
      <form onSubmit={onLookup} className="space-y-4" noValidate>
        <div className="space-y-1">
          <label htmlFor="postcode" className="block text-sm font-medium">
            Postcode
          </label>
          <input
            id="postcode"
            name="postcode"
            type="text"
            inputMode="text"
            autoComplete="postal-code"
            autoCapitalize="characters"
            placeholder="SW1A 1AA"
            value={postcode}
            onChange={(e) => setPostcode(e.target.value)}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "postcode-error" : undefined}
            className="border-input w-full max-w-xs rounded-md border px-3 py-2 uppercase"
          />
        </div>
        {error && (
          <p id="postcode-error" role="alert" className="text-risk text-sm">
            {error}
          </p>
        )}
        <Button type="submit" disabled={busy || postcode.trim() === ""}>
          {busy ? "Looking up…" : "Find my address"}
        </Button>
        {postcode.trim() !== "" && !isPlausiblePostcode(postcode) && !error && (
          <p className="text-muted-foreground text-sm">
            That doesn&apos;t look like a full postcode yet.
          </p>
        )}
      </form>
    )
  }

  if (step.kind === "addresses") {
    const { lookup } = step
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p>
            Addresses for <strong>{lookup.postcode}</strong>
          </p>
          <button
            type="button"
            className="text-deep text-sm underline underline-offset-4"
            onClick={() => setStep({ kind: "postcode" })}
          >
            Change postcode
          </button>
        </div>
        {lookup.addresses.length === 0 ? (
          <p className="text-muted-foreground">
            We don&apos;t have any addresses on file for this postcode.
          </p>
        ) : (
          <ul className="space-y-2">
            {lookup.addresses.map((a) => (
              <li key={a.uprn ?? a.line1}>
                <button
                  type="button"
                  onClick={() => chooseAddress(lookup, a)}
                  className="border-input hover:bg-mint flex w-full items-center justify-between rounded-md border px-3 py-2 text-left"
                >
                  <span>{a.line1}</span>
                  {a.epc_rating && (
                    <span className="bg-mint text-deep rounded-full px-2 py-0.5 text-xs font-semibold">
                      EPC {a.epc_rating}
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="text-deep text-sm underline underline-offset-4"
          onClick={() => setStep({ kind: "manual", lookup })}
        >
          My address isn&apos;t listed
        </button>
      </div>
    )
  }

  return <ManualPropertyForm lookup={step.lookup} onSubmit={goToHousehold} />
}

function ManualPropertyForm({
  lookup,
  onSubmit,
}: {
  lookup: PostcodeLookup
  onSubmit: (address: AddressInput, property: PropertyFactsInput) => void
}) {
  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const line1 = String(form.get("line1") ?? "").trim()
    if (!line1) return
    const address: AddressInput = {
      line1,
      postcode: lookup.postcode,
      lat: lookup.lat,
      lon: lookup.lon,
      local_authority: lookup.local_authority,
      country: guessCountry(lookup.postcode),
      uprn: null,
    }
    const epcRating = form.get("epc_rating")
    const property: PropertyFactsInput = {
      property_type: form.get("property_type") as PropertyFactsInput["property_type"],
      source: "user",
      epc_rating: epcRating ? (epcRating as PropertyFactsInput["epc_rating"]) : null,
    }
    onSubmit(address, property)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <p className="text-muted-foreground text-sm">
        Tell us a little about {lookup.postcode} and we will fill in the rest where we can.
      </p>
      <div className="space-y-1">
        <label htmlFor="line1" className="block text-sm font-medium">
          Address line 1
        </label>
        <input
          id="line1"
          name="line1"
          type="text"
          required
          autoComplete="address-line1"
          className="border-input w-full rounded-md border px-3 py-2"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="property_type" className="block text-sm font-medium">
          Property type
        </label>
        <select
          id="property_type"
          name="property_type"
          required
          defaultValue=""
          className="border-input w-full rounded-md border px-3 py-2"
        >
          <option value="" disabled>
            Select one
          </option>
          {PROPERTY_TYPES.map((t) => (
            <option key={t} value={t}>
              {t.replace("_", " ")}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <label htmlFor="epc_rating" className="block text-sm font-medium">
          Energy certificate (EPC) rating, if you know it
        </label>
        <select
          id="epc_rating"
          name="epc_rating"
          defaultValue=""
          className="border-input w-full max-w-xs rounded-md border px-3 py-2"
        >
          <option value="">I don&apos;t know</option>
          {EPC_RATINGS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
      </div>
      <Button type="submit">Continue</Button>
    </form>
  )
}
