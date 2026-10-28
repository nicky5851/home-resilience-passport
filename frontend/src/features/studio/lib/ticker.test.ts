import { describe, expect, it } from "vitest"

import { easeOut, tickerValue } from "@/features/studio/lib/ticker"

describe("easeOut", () => {
  it("starts at 0 and ends at 1", () => {
    expect(easeOut(0)).toBe(0)
    expect(easeOut(1)).toBe(1)
  })

  it("clamps outside [0, 1]", () => {
    expect(easeOut(-1)).toBe(0)
    expect(easeOut(2)).toBe(1)
  })

  it("is ahead of linear partway through (ease-out)", () => {
    expect(easeOut(0.5)).toBeGreaterThan(0.5)
  })
})

describe("tickerValue", () => {
  it("is `from` at elapsed 0 and `to` at or after the duration", () => {
    expect(tickerValue(0, 100, 0, 640)).toBe(0)
    expect(tickerValue(0, 100, 640, 640)).toBe(100)
    expect(tickerValue(0, 100, 1000, 640)).toBe(100)
  })

  it("returns `to` immediately when duration is 0", () => {
    expect(tickerValue(10, 50, 0, 0)).toBe(50)
  })
})
