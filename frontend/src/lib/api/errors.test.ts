import { describe, expect, it } from "vitest"

import { ApiError } from "@/lib/api/errors"
import { loginPath, safeNext } from "@/lib/auth/use-user"

describe("ApiError.from", () => {
  it("keeps the contract body", () => {
    const e = ApiError.from(404, { detail: "We couldn't find that home.", code: "not_found" })
    expect([e.status, e.code, e.detail]).toEqual([404, "not_found", "We couldn't find that home."])
  })

  it("falls back when the body is not the contract shape", () => {
    expect(ApiError.from(502, "<html>").code).toBe("internal")
    expect(ApiError.from(400, { detail: [{ msg: "x" }] }).detail).toMatch(/Something went wrong/)
  })
})

describe("login redirects", () => {
  it("builds /login?next=", () => {
    expect(loginPath("/homes?x=1")).toBe("/login?next=%2Fhomes%3Fx%3D1")
  })

  it("only allows same-site paths as next", () => {
    expect(safeNext("/homes")).toBe("/homes")
    expect(safeNext("https://evil.example")).toBe("/")
    expect(safeNext("//evil.example")).toBe("/")
    expect(safeNext(null)).toBe("/")
  })
})
