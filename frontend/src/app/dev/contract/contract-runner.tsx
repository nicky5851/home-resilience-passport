"use client"

import { useCallback, useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { api, MOCK_MODE } from "@/lib/api/client"
import { CHECKS, runContractChecks, type CheckResult } from "@/lib/api/contract-checks"

export function ContractRunner() {
  const [results, setResults] = useState<CheckResult[]>([])
  const [running, setRunning] = useState(false)

  const run = useCallback(async () => {
    setRunning(true)
    setResults([])
    await runContractChecks(api, (r) => setResults((prev) => [...prev, r]))
    setRunning(false)
  }, [])

  useEffect(() => {
    void run()
  }, [run])

  const passed = results.filter((r) => r.ok).length
  const done = !running && results.length === CHECKS.length

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="bg-mint text-deep rounded-full px-3 py-1 text-sm font-medium">
          {MOCK_MODE ? "Mock mode (fixtures)" : "Real API"}
        </span>
        <span aria-live="polite" className="text-sm" data-testid="summary">
          {done
            ? `${passed} of ${CHECKS.length} passed`
            : `Running… ${results.length}/${CHECKS.length}`}
        </span>
        <Button variant="outline" size="sm" onClick={() => void run()} disabled={running}>
          Run again
        </Button>
      </div>
      <ol className="divide-border border-border divide-y rounded-md border">
        {CHECKS.map((c, i) => {
          const r = results[i]
          return (
            <li key={c.name} className="flex gap-3 px-3 py-2 text-sm">
              <span
                aria-label={r ? (r.ok ? "passed" : "failed") : "pending"}
                className={r ? (r.ok ? "text-green" : "text-risk") : "text-muted-foreground"}
              >
                {r ? (r.ok ? "✔" : "✘") : "…"}
              </span>
              <span className="font-medium">{c.name}</span>
              {r && <span className="text-muted-foreground ml-auto text-right">{r.detail}</span>}
            </li>
          )
        })}
      </ol>
    </div>
  )
}
