import { describe, expect, it } from "vitest"

import { makeClient } from "@/lib/api/client"
import { CHECKS, runContractChecks } from "@/lib/api/contract-checks"
import { mockFetch } from "@/mocks/handler"

/** A fetch for Node that keeps cookies and sends an Origin, like the browser does. */
function browserLikeFetch(origin: string): typeof fetch {
  const jar = new Map<string, string>()
  return async (input, init) => {
    const req = new Request(input, init)
    req.headers.set("Origin", origin)
    if (jar.size) req.headers.set("Cookie", [...jar].map(([k, v]) => `${k}=${v}`).join("; "))
    const res = await fetch(req)
    for (const c of res.headers.getSetCookie()) {
      const [pair] = c.split(";")
      const [k, v] = pair!.split("=")
      if (v === "" || v === '""' || /Max-Age=0/i.test(c)) jar.delete(k!)
      else jar.set(k!, v!)
    }
    return res
  }
}

function report(results: { name: string; ok: boolean; detail: string }[]) {
  return results.filter((r) => !r.ok).map((r) => `${r.name}: ${r.detail}`)
}

describe("contract checks", () => {
  it("all pass in mock mode", async () => {
    const results = await runContractChecks(
      makeClient({ baseUrl: "http://mock.local", fetch: mockFetch }),
    )
    expect(results).toHaveLength(CHECKS.length)
    expect(report(results)).toEqual([])
  })

  // Set CONTRACT_API_URL=http://localhost:8000 (with `make api` running) to check the real API.
  const real = process.env.CONTRACT_API_URL
  it.skipIf(!real)("all pass against the real API", async () => {
    const origin = process.env.CONTRACT_ORIGIN ?? "http://localhost:3000"
    const results = await runContractChecks(
      makeClient({ baseUrl: real, fetch: browserLikeFetch(origin) }),
    )
    expect(report(results)).toEqual([])
  })
})
