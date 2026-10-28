"use client"

import { useState } from "react"

import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"

/** "Share" / "Stop sharing" (spec L13). */
export function ShareControls({
  homeId,
  shareToken,
  onChange,
}: {
  homeId: string
  shareToken: string | null
  onChange: (token: string | null) => void
}) {
  const [url, setUrl] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function share() {
    setBusy(true)
    setError(null)
    try {
      const result = unwrap(
        await api.POST("/api/v1/homes/{home_id}/share", { params: { path: { home_id: homeId } } }),
      )
      setUrl(result.url)
      onChange(result.share_token)
      await navigator.clipboard.writeText(result.url)
      setCopied(true)
    } catch (e) {
      setError(isApiError(e) ? e.detail : "Could not share this passport.")
    } finally {
      setBusy(false)
    }
  }

  async function stopSharing() {
    setBusy(true)
    setError(null)
    try {
      unwrap(
        await api.DELETE("/api/v1/homes/{home_id}/share", {
          params: { path: { home_id: homeId } },
        }),
      )
      setUrl(null)
      setCopied(false)
      onChange(null)
    } catch (e) {
      setError(isApiError(e) ? e.detail : "Could not stop sharing.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2">
      {shareToken ? (
        <div className="space-y-2">
          {copied && <p role="status">Link copied to your clipboard.</p>}
          {url && <p className="text-muted-foreground text-sm break-all">{url}</p>}
          <Button type="button" variant="outline" disabled={busy} onClick={stopSharing}>
            Stop sharing
          </Button>
        </div>
      ) : (
        <Button type="button" disabled={busy} onClick={share}>
          {busy ? "Sharing…" : "Share"}
        </Button>
      )}
      {error && (
        <p role="alert" className="text-risk text-sm">
          {error}
        </p>
      )}
    </div>
  )
}
