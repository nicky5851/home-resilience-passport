"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

import { RequireUser } from "@/components/auth/require-user"
import { Button } from "@/components/ui/button"
import { api, unwrap } from "@/lib/api/client"
import { isApiError } from "@/lib/api/errors"
import type { UserRead } from "@/lib/api/types"
import { useUser } from "@/lib/auth/use-user"

export function AccountPage() {
  return <RequireUser>{(u) => <AccountBody user={u} />}</RequireUser>
}

function AccountBody({ user }: { user: UserRead }) {
  const router = useRouter()
  const userState = useUser()
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [confirmText, setConfirmText] = useState("")
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  async function downloadData() {
    setDownloadError(null)
    try {
      const data = unwrap(await api.GET("/api/v1/users/me/export"))
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "home-resilience-passport-data.json"
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setDownloadError(isApiError(e) ? e.detail : "Could not download your data.")
    }
  }

  async function deleteAccount() {
    setDeleting(true)
    setDeleteError(null)
    try {
      unwrap(await api.DELETE("/api/v1/users/me"))
      await userState.refresh()
      router.push("/")
    } catch (e) {
      setDeleteError(isApiError(e) ? e.detail : "Could not delete your account.")
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-8">
      <p className="text-muted-foreground">Signed in as {user.email}</p>

      <div className="space-y-2">
        <h2 className="font-semibold">Your data</h2>
        <Button type="button" variant="outline" onClick={downloadData}>
          Download my data
        </Button>
        {downloadError && (
          <p role="alert" className="text-risk text-sm">
            {downloadError}
          </p>
        )}
      </div>

      <div className="border-risk/30 space-y-2 rounded-md border p-4">
        <h2 className="text-risk font-semibold">Delete my account</h2>
        <p className="text-muted-foreground text-sm">
          This permanently deletes your account and all of your homes. This cannot be undone.
        </p>
        <label htmlFor="confirm-delete" className="block text-sm font-medium">
          Type DELETE to confirm
        </label>
        <input
          id="confirm-delete"
          value={confirmText}
          onChange={(e) => setConfirmText(e.target.value)}
          className="border-input w-full max-w-xs rounded-md border px-3 py-2"
        />
        {deleteError && (
          <p role="alert" className="text-risk text-sm">
            {deleteError}
          </p>
        )}
        <Button
          type="button"
          variant="destructive"
          disabled={confirmText !== "DELETE" || deleting}
          onClick={deleteAccount}
        >
          {deleting ? "Deleting…" : "Delete my account"}
        </Button>
      </div>
    </div>
  )
}
