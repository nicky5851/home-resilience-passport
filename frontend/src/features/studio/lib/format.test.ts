import { describe, expect, it } from "vitest"

import { formatDate, formatGbp, formatNumber } from "@/features/studio/lib/format"

describe("formatGbp", () => {
  it("adds the pound sign and thousands separators", () => {
    expect(formatGbp(1234)).toBe("£1,234")
    expect(formatGbp(0)).toBe("£0")
  })

  it("rounds and keeps the minus sign outside the symbol", () => {
    expect(formatGbp(-45.6)).toBe("-£46")
  })
})

describe("formatNumber", () => {
  it("formats with en-GB grouping", () => {
    expect(formatNumber(12345)).toBe("12,345")
  })
})

describe("formatDate", () => {
  it("formats an ISO date as day month year", () => {
    expect(formatDate("2026-10-28")).toBe("28 Oct 2026")
  })
})
