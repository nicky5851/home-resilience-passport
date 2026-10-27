// Mock mode (NEXT_PUBLIC_API_MOCK=1): a fetch that answers /api/v1/... from the demo fixtures,
// following the same contract as N's stub API (CONTRACT §3–§4). State lives in memory, and the
// logged-in user in sessionStorage so it survives client-side navigation and reloads.
import type { ErrorCode, PassportEvent } from "@/lib/api/types"
import { fixtures } from "@/mocks/fixtures"
import type { DemoFixture } from "@/mocks/types"

const STUB_USER_ID = "00000000-0000-0000-0000-000000000001"
const USER_KEY = "hrp_mock_user"
const UNSUPPORTED = /^(AB|DD|DG|EH|FK|G|HS|IV|KA|KW|KY|ML|PA|PH|TD|ZE|BT)[0-9]/
const POSTCODE = /^([A-Z]{1,2}[0-9][A-Z0-9]?)([0-9][A-Z]{2})$/

type MockHome = {
  id: string
  owner: string | null // null = demo home any logged-in user can open
  fixture: DemoFixture
  line1: string
  postcode: string
  assessed: boolean
  shareToken: string | null
  events: PassportEvent[]
}

let memoryUser: string | null = null
const homes = new Map<string, MockHome>()
for (const f of fixtures) {
  homes.set(f.passport.home_id, {
    id: f.passport.home_id,
    owner: null,
    fixture: f,
    line1: f.address.line1,
    postcode: f.address.postcode,
    assessed: true,
    shareToken: null,
    events: [...f.passport.events],
  })
}

function getUser(): string | null {
  if (typeof sessionStorage !== "undefined") return sessionStorage.getItem(USER_KEY)
  return memoryUser
}

function setUser(email: string | null): void {
  memoryUser = email
  if (typeof sessionStorage === "undefined") return
  if (email) sessionStorage.setItem(USER_KEY, email)
  else sessionStorage.removeItem(USER_KEY)
}

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  if (status === 204 || body === undefined) return new Response(null, { status, headers })
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  })
}

function error(status: number, code: ErrorCode, detail: string): Response {
  return json(status, { detail, code })
}

function normalisePostcode(raw: string): string | null {
  const m = POSTCODE.exec(raw.replace(/\s+/g, "").toUpperCase())
  return m ? `${m[1]} ${m[2]}` : null
}

function now(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z")
}

function passportOf(h: MockHome) {
  return {
    ...h.fixture.passport,
    home_id: h.id,
    address: { ...h.fixture.address, line1: h.line1 },
    events: h.events,
    share_token: h.shareToken,
  }
}

async function readJson(req: Request): Promise<Record<string, unknown>> {
  const text = await req.text()
  return text ? (JSON.parse(text) as Record<string, unknown>) : {}
}

const user = () => ({
  id: STUB_USER_ID,
  email: getUser() ?? "",
  is_active: true,
  is_superuser: false,
  is_verified: false,
})

export async function mockFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const req = input instanceof Request ? input : new Request(input, init)
  const url = new URL(req.url, "http://mock.local")
  const path = url.pathname.replace(/^\/api\/v1/, "")
  const method = req.method.toUpperCase()
  const route = `${method} ${path}`
  let m: RegExpExecArray | null

  // --- Public ------------------------------------------------------------------------------
  if (route === "GET /health") return json(200, { status: "ok" })
  if (route === "GET /demo/homes")
    return json(
      200,
      fixtures.map((f) => ({
        slug: f.slug,
        hazard_shown: f.hazard_shown,
        address: f.address,
        household: f.household,
        property: f.property,
        risk: f.risk,
        score: f.score,
        plan: f.plan,
        funding: f.funding,
      })),
    )
  if (route === "GET /model/info")
    return json(200, { version: "stub", trained_on: "not trained yet", metrics: {} })
  if ((m = /^GET \/lookup\/postcode\/([^/]+)$/.exec(route))) {
    const pc = normalisePostcode(decodeURIComponent(m[1]!))
    if (!pc) return error(400, "validation", "Enter a full UK postcode, for example SW1A 1AA.")
    if (UNSUPPORTED.test(pc))
      return error(
        400,
        "unsupported_region",
        "Home Resilience Passport covers England and Wales for now.",
      )
    const f = fixtures.find((x) => x.address.postcode === pc)
    if (!f)
      return json(200, {
        postcode: pc,
        lat: 51.5072,
        lon: -0.1276,
        local_authority: null,
        addresses: [],
      })
    const a = f.address
    return json(200, {
      postcode: pc,
      lat: a.lat,
      lon: a.lon,
      local_authority: a.local_authority,
      addresses: [{ line1: a.line1, uprn: a.uprn, epc_rating: f.property.epc_rating }],
    })
  }
  if ((m = /^GET \/public\/passport\/([^/]+)$/.exec(route))) {
    const h = [...homes.values()].find((x) => x.shareToken === m![1])
    if (!h) return error(404, "not_found", "This link is no longer active.")
    const { household: _h, share_token: _t, ...rest } = passportOf(h)
    void _h
    void _t
    return json(200, {
      ...rest,
      events: rest.events.map((e) => {
        const { certificate_name: _c, ...detail } = e.detail as Record<string, unknown>
        void _c
        return { ...e, detail }
      }),
    })
  }

  // --- Auth --------------------------------------------------------------------------------
  if (route === "POST /auth/register") {
    const body = await readJson(req)
    if (body.accept_privacy !== true)
      return error(400, "validation", "Please confirm you have read the privacy notice.")
    return json(201, { ...user(), email: String(body.email ?? "") })
  }
  if (route === "POST /auth/login") {
    const form = new URLSearchParams(await req.text())
    const email = form.get("username")?.trim()
    if (!email || !form.get("password"))
      return error(400, "validation", "Email or password is incorrect")
    setUser(email)
    return json(204, undefined)
  }
  if (route === "POST /auth/logout") {
    setUser(null)
    return json(204, undefined)
  }
  if (route === "POST /auth/forgot-password") return json(202, null)
  if (route === "POST /auth/reset-password") return json(200, null)

  // --- Everything below needs login ----------------------------------------------------------
  const email = getUser()
  if (!email) return error(401, "unauthorised", "Please log in to continue.")

  if (route === "GET /users/me") return json(200, user())
  if (route === "GET /users/me/export")
    return json(200, {
      user: user(),
      homes: [...homes.values()].filter((h) => h.owner === email).map(passportOf),
    })
  if (route === "DELETE /users/me") {
    for (const h of homes.values()) if (h.owner === email) homes.delete(h.id)
    setUser(null)
    return json(204, undefined)
  }
  if (route === "GET /homes")
    return json(
      200,
      [...homes.values()]
        .filter((h) => h.owner === email)
        .map((h) => ({
          home_id: h.id,
          line1: h.line1,
          postcode: h.postcode,
          score: h.assessed ? h.fixture.score : null,
        })),
    )
  if (route === "POST /homes") {
    const body = (await readJson(req)) as { address?: { line1?: string; postcode?: string } }
    const pc = normalisePostcode(body.address?.postcode ?? "")
    if (!body.address?.line1 || !pc) return error(400, "validation", "address: Field required")
    const f = fixtures.find((x) => x.address.postcode === pc) ?? fixtures[0]!
    const id = crypto.randomUUID()
    homes.set(id, {
      id,
      owner: email,
      fixture: f,
      line1: body.address.line1,
      postcode: pc,
      assessed: false,
      shareToken: null,
      events: [],
    })
    return json(201, { home_id: id })
  }

  if ((m = /^(GET|POST|DELETE) \/homes\/([^/]+)(\/.*)?$/.exec(route))) {
    const h = homes.get(m[2]!)
    if (!h || (h.owner !== null && h.owner !== email))
      return error(404, "not_found", "We couldn't find that home.")
    const sub = `${method} ${m[3] ?? ""}`
    const f = h.fixture
    switch (sub) {
      case "DELETE ":
        if (h.owner === null) return error(404, "not_found", "We couldn't find that home.")
        homes.delete(h.id)
        return json(204, undefined)
      case "POST /assess":
        h.assessed = true
        h.events.push({
          id: crypto.randomUUID(),
          kind: "assessed",
          at: now(),
          score_after: f.score.value,
          detail: {},
        })
        return json(200, { risk: f.risk, score: f.score, inputs: f.inputs })
      case "GET /risk":
        if (!h.assessed) return error(404, "not_found", "This home has not been assessed yet.")
        return json(200, { risk: f.risk, score: f.score, inputs: f.inputs })
      case "POST /plan":
        return json(200, f.plan)
      case "POST /funding":
        return json(200, f.funding)
      case "GET /passport":
        return json(200, passportOf(h))
      case "POST /share": {
        h.shareToken = crypto.randomUUID().replace(/-/g, "")
        h.events.push({
          id: crypto.randomUUID(),
          kind: "shared",
          at: now(),
          score_after: null,
          detail: {},
        })
        const origin = typeof location !== "undefined" ? location.origin : "http://localhost:3000"
        return json(200, { share_token: h.shareToken, url: `${origin}/p/${h.shareToken}` })
      }
      case "DELETE /share":
        h.shareToken = null
        return json(204, undefined)
    }
  }

  return error(404, "not_found", "We couldn't find that.")
}
