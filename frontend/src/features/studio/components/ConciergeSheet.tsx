"use client"

import { usePathname } from "next/navigation"
import { useState } from "react"

import { studioApi, unwrap } from "@/features/studio/api/client"
import type { ConciergeCitation, ConciergeMessage } from "@/features/studio/api/types"

const SUGGESTIONS = [
  "What's my biggest risk?",
  "What's the cheapest way to cut my bills?",
  "What should I do next?",
]

type ChatMessage = ConciergeMessage & { citations?: ConciergeCitation[]; source?: string }

/** Extracts the home ref from a Studio URL, e.g. /studio/demo-flood-terrace/s16-week-ahead.
 * `null` on the hub or the ref-less Compare page, where there's no home to ask about. */
function refFromPath(pathname: string): string | null {
  const parts = pathname.split("/").filter(Boolean)
  if (parts[0] !== "studio" || parts.length < 2) return null
  if (parts[1] === "compare") return null
  return parts[1]
}

export function ConciergeSheet() {
  const pathname = usePathname()
  const ref = refFromPath(pathname ?? "")
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState("")
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!ref) return null
  const homeRef: string = ref

  async function send(text: string) {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    const next: ChatMessage[] = [...messages, { role: "user", content: trimmed }]
    setMessages(next)
    setDraft("")
    setSending(true)
    setError(null)
    try {
      const reply = unwrap(
        await studioApi.POST("/api/v1/studio/homes/{ref}/concierge", {
          params: { path: { ref: homeRef } },
          body: { messages: next.map(({ role, content }) => ({ role, content })) },
        }),
      )
      setMessages([
        ...next,
        {
          role: "assistant",
          content: reply.answer,
          citations: reply.citations,
          source: reply.source,
        },
      ])
    } catch {
      setError("We couldn't get an answer just now. Please try again.")
    } finally {
      setSending(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className="s-focus-ring fixed right-6 bottom-6 z-40 rounded-full px-5 py-3 text-sm font-medium shadow-lg"
        style={{ background: "var(--s-green-700)", color: "var(--s-paper)" }}
        onClick={() => setOpen(true)}
        aria-label="Ask your Passport"
      >
        Ask
      </button>
      {open ? (
        <div
          className="fixed inset-0 z-50 flex justify-end"
          role="dialog"
          aria-label="Ask your Passport"
        >
          <button
            type="button"
            className="flex-1"
            style={{ background: "rgba(0,0,0,0.3)" }}
            aria-label="Close"
            onClick={() => setOpen(false)}
          />
          <div
            className="flex h-full w-full max-w-md flex-col p-5"
            style={{ background: "var(--s-paper)" }}
          >
            <div className="flex items-center justify-between">
              <h2 className="s-display text-xl">Ask about your home</h2>
              <button
                type="button"
                className="s-focus-ring text-sm underline"
                onClick={() => setOpen(false)}
              >
                Close
              </button>
            </div>

            <div className="mt-4 flex-1 space-y-3 overflow-y-auto">
              {messages.length === 0 ? (
                <div className="flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="s-focus-ring rounded-full border px-3 py-1 text-sm"
                      style={{ borderColor: "var(--s-stone-200)" }}
                      onClick={() => send(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              ) : null}
              {messages.map((m, i) => (
                <div key={i} className="s-card">
                  <p className="text-sm">{m.content}</p>
                  {m.citations && m.citations.length > 0 ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.citations.map((c) => (
                        <span
                          key={c.tool}
                          className="s-mono rounded-full px-2 py-0.5 text-xs"
                          style={{ background: "var(--s-green-100)", color: "var(--s-green-700)" }}
                        >
                          From: {c.label}
                        </span>
                      ))}
                    </div>
                  ) : null}
                  {m.source === "template" ? (
                    <span
                      className="s-mono mt-2 inline-block rounded-full px-2 py-0.5 text-xs"
                      style={{ background: "var(--s-stone-200)" }}
                    >
                      Template mode
                    </span>
                  ) : null}
                </div>
              ))}
              {error ? (
                <p className="text-sm" style={{ color: "var(--s-risk-high)" }}>
                  {error}
                </p>
              ) : null}
            </div>

            <form
              className="mt-4 flex gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                send(draft)
              }}
            >
              <input
                className="s-focus-ring flex-1 rounded border px-2 py-2 text-sm"
                style={{ borderColor: "var(--s-stone-200)" }}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Don't include personal details"
                disabled={sending}
              />
              <button
                type="submit"
                className="s-focus-ring rounded px-3 py-2 text-sm font-medium"
                style={{ background: "var(--s-green-700)", color: "var(--s-paper)" }}
                disabled={sending || !draft.trim()}
              >
                {sending ? "…" : "Send"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </>
  )
}
