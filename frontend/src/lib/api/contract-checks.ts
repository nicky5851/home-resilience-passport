// Every seam in CONTRACT.md, exercised end to end. Used by the /dev/contract page and by
// contract-checks.test.ts (against mock mode, and against the real API when one is running).
import { login, unwrap, type ApiClient } from "@/lib/api/client"
import { ApiError } from "@/lib/api/errors"
import type { DemoHome } from "@/lib/api/types"

export type CheckResult = { name: string; ok: boolean; detail: string }

type Check = { name: string; run: (ctx: Ctx) => Promise<string> }
type Ctx = { api: ApiClient; demo?: DemoHome; homeId?: string; shareToken?: string }

const HAZARDS = ["river_sea_flood", "overheating", "storm", "subsidence", "surface_water"]

function expect(cond: unknown, msg: string): asserts cond {
  if (!cond) throw new Error(msg)
}

async function expectError(p: Promise<unknown>, status: number, code: string): Promise<string> {
  try {
    await p
  } catch (e) {
    expect(e instanceof ApiError, `expected ApiError, got ${String(e)}`)
    expect(e.status === status && e.code === code, `got ${e.status} ${e.code}`)
    expect(typeof e.detail === "string" && e.detail.length > 0, "detail must be a string")
    return `${e.status} ${e.code}: ${e.detail}`
  }
  throw new Error(`expected ${status} ${code}, but the call succeeded`)
}

const homePath = (ctx: Ctx) => ({ params: { path: { home_id: ctx.homeId! } } })

export const CHECKS: Check[] = [
  {
    name: "GET /health",
    run: async ({ api }) => {
      const d = unwrap(await api.GET("/api/v1/health"))
      expect(d.status === "ok", "status is not ok")
      return "ok"
    },
  },
  {
    name: "GET /demo/homes (5 homes, no login)",
    run: async (ctx) => {
      const homes = unwrap(await ctx.api.GET("/api/v1/demo/homes"))
      expect(homes.length === 5, `got ${homes.length} homes`)
      ctx.demo = homes[0]
      return homes.map((h) => h.slug).join(", ")
    },
  },
  {
    name: "Logged out: GET /users/me → 401",
    run: async ({ api }) => {
      await api.POST("/api/v1/auth/logout")
      return expectError(api.GET("/api/v1/users/me").then(unwrap), 401, "unauthorised")
    },
  },
  {
    name: "POST /auth/register without privacy → 400",
    run: ({ api }) =>
      expectError(
        api
          .POST("/api/v1/auth/register", {
            body: {
              email: "contract@example.com",
              password: "long-enough-pw",
              accept_privacy: false,
            },
          })
          .then(unwrap),
        400,
        "validation",
      ),
  },
  {
    name: "POST /auth/register → 201",
    run: async ({ api }) => {
      const u = unwrap(
        await api.POST("/api/v1/auth/register", {
          body: { email: "contract@example.com", password: "long-enough-pw", accept_privacy: true },
        }),
      )
      return u.email
    },
  },
  {
    name: "POST /auth/login (form) → GET /users/me",
    run: async ({ api }) => {
      await login(api, "contract@example.com", "long-enough-pw")
      const me = unwrap(await api.GET("/api/v1/users/me"))
      expect(me.email === "contract@example.com", `me is ${me.email}`)
      return `${me.email} (${me.id})`
    },
  },
  {
    name: "GET /lookup/postcode (any spacing)",
    run: async ({ api, demo }) => {
      const pc = demo!.address.postcode.replace(" ", "").toLowerCase()
      const d = unwrap(
        await api.GET("/api/v1/lookup/postcode/{postcode}", { params: { path: { postcode: pc } } }),
      )
      expect(d.postcode === demo!.address.postcode, `postcode is ${d.postcode}`)
      return `${d.postcode}: ${d.addresses.length} address(es)`
    },
  },
  {
    name: "Bad postcode → 400 validation",
    run: ({ api }) =>
      expectError(
        api
          .GET("/api/v1/lookup/postcode/{postcode}", { params: { path: { postcode: "nonsense" } } })
          .then(unwrap),
        400,
        "validation",
      ),
  },
  {
    name: "Scottish postcode → 400 unsupported_region",
    run: ({ api }) =>
      expectError(
        api
          .GET("/api/v1/lookup/postcode/{postcode}", { params: { path: { postcode: "EH1 1YZ" } } })
          .then(unwrap),
        400,
        "unsupported_region",
      ),
  },
  {
    name: "POST /homes → 201",
    run: async (ctx) => {
      const { address, household, property } = ctx.demo!
      const d = unwrap(
        await ctx.api.POST("/api/v1/homes", {
          body: { address, household, property_override: property },
        }),
      )
      ctx.homeId = d.home_id
      return d.home_id
    },
  },
  {
    name: "GET /homes/{id}/risk before assessment → 404",
    run: (ctx) =>
      expectError(
        ctx.api.GET("/api/v1/homes/{home_id}/risk", homePath(ctx)).then(unwrap),
        404,
        "not_found",
      ),
  },
  {
    name: "POST /homes/{id}/assess",
    run: async (ctx) => {
      const d = unwrap(await ctx.api.POST("/api/v1/homes/{home_id}/assess", homePath(ctx)))
      expect(
        d.risk.levels.map((l) => l.hazard).join() === HAZARDS.join(),
        "hazards are not in contract order",
      )
      return `score ${d.score.value} (${d.score.band})`
    },
  },
  {
    name: "POST /homes/{id}/plan",
    run: async (ctx) => {
      const p = unwrap(
        await ctx.api.POST("/api/v1/homes/{home_id}/plan", { ...homePath(ctx), body: {} }),
      )
      return `${p.items.length} measures, £${p.total_cost_low_gbp}–£${p.total_cost_high_gbp}`
    },
  },
  {
    name: "POST /homes/{id}/funding",
    run: async (ctx) => {
      const f = unwrap(
        await ctx.api.POST("/api/v1/homes/{home_id}/funding", {
          ...homePath(ctx),
          body: { selected_ids: [] },
        }),
      )
      return `covered £${f.covered_gbp}, gap £${f.gap_gbp}`
    },
  },
  {
    name: "GET /homes/{id}/passport",
    run: async (ctx) => {
      const p = unwrap(await ctx.api.GET("/api/v1/homes/{home_id}/passport", homePath(ctx)))
      expect(p.home_id === ctx.homeId, "wrong home")
      return `${p.events.length} event(s)`
    },
  },
  {
    name: "Share → public passport has no household → stop sharing",
    run: async (ctx) => {
      const s = unwrap(await ctx.api.POST("/api/v1/homes/{home_id}/share", homePath(ctx)))
      const path = { params: { path: { share_token: s.share_token } } }
      const pub = unwrap(await ctx.api.GET("/api/v1/public/passport/{share_token}", path))
      expect(!("household" in pub), "public passport contains household")
      unwrap(await ctx.api.DELETE("/api/v1/homes/{home_id}/share", homePath(ctx)))
      await expectError(
        ctx.api.GET("/api/v1/public/passport/{share_token}", path).then(unwrap),
        404,
        "not_found",
      )
      return "revoked link → 404"
    },
  },
  {
    name: "Unknown home → 404 not_found",
    run: ({ api }) =>
      expectError(
        api
          .GET("/api/v1/homes/{home_id}/passport", {
            params: { path: { home_id: "00000000-0000-4000-8000-000000000000" } },
          })
          .then(unwrap),
        404,
        "not_found",
      ),
  },
  {
    name: "GET /model/info",
    run: async ({ api }) => {
      const d = unwrap(await api.GET("/api/v1/model/info"))
      return `version ${d.version}`
    },
  },
  {
    name: "DELETE /homes/{id} → logout → 401",
    run: async (ctx) => {
      unwrap(await ctx.api.DELETE("/api/v1/homes/{home_id}", homePath(ctx)))
      unwrap(await ctx.api.POST("/api/v1/auth/logout"))
      return expectError(ctx.api.GET("/api/v1/users/me").then(unwrap), 401, "unauthorised")
    },
  },
]

/** Run every check in order; later checks reuse ids from earlier ones. */
export async function runContractChecks(
  api: ApiClient,
  onResult?: (r: CheckResult) => void,
): Promise<CheckResult[]> {
  const ctx: Ctx = { api }
  const results: CheckResult[] = []
  for (const check of CHECKS) {
    let r: CheckResult
    try {
      r = { name: check.name, ok: true, detail: await check.run(ctx) }
    } catch (e) {
      r = { name: check.name, ok: false, detail: e instanceof Error ? e.message : String(e) }
    }
    results.push(r)
    onResult?.(r)
  }
  return results
}
