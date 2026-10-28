"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { Measure } from "@/lib/api/types"

/** "Record completed work" with an optional certificate upload (CONTRACT §6). */
export function RecordWorkForm({
  homeId,
  measures,
  onRecorded,
}: {
  homeId: string
  measures: Measure[]
  onRecorded: () => void
}) {
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    setBusy(true)
    setError(null)
    try {
      unwrap(
        await api.POST("/api/v1/homes/{home_id}/work", {
          params: { path: { home_id: homeId } },
          // openapi-fetch passes a FormData body straight through and lets the browser set the
          // multipart Content-Type and boundary itself.
          body: form as unknown as never,
        }),
      )
      e.currentTarget.reset()
      onRecorded()
    } catch (err) {
      setError(isApiError(err) ? err.detail : "Something went wrong. Please try again.")
    } finally {
      setBusy(false)
    }
  }

  if (measures.length === 0) return null

  return (
    <form onSubmit={onSubmit} className="space-y-4" noValidate>
      <div className="space-y-1">
        <label htmlFor="measure_id" className="block text-sm font-medium">
          What did you complete?
        </label>
        <select
          id="measure_id"
          name="measure_id"
          required
          defaultValue=""
          className="border-input w-full max-w-sm rounded-md border px-3 py-2"
        >
          <option value="" disabled>
            Select one
          </option>
          {measures.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-1">
        <label htmlFor="completed_on" className="block text-sm font-medium">
          Date completed
        </label>
        <input
          id="completed_on"
          name="completed_on"
          type="date"
          required
          max={new Date().toISOString().slice(0, 10)}
          className="border-input w-full max-w-xs rounded-md border px-3 py-2"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="cost_gbp" className="block text-sm font-medium">
          Cost (£, optional)
        </label>
        <input
          id="cost_gbp"
          name="cost_gbp"
          type="number"
          min={0}
          className="border-input w-full max-w-xs rounded-md border px-3 py-2"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="certificate" className="block text-sm font-medium">
          Certificate (PDF, JPEG or PNG, up to 5 MB, optional)
        </label>
        <input id="certificate" name="certificate" type="file" accept=".pdf,.jpg,.jpeg,.png" />
      </div>
      {error && (
        <p role="alert" className="text-risk text-sm">
          {error}
        </p>
      )}
      <Button type="submit" disabled={busy}>
        {busy ? "Saving…" : "Record completed work"}
      </Button>
    </form>
  )
}
