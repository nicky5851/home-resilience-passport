import { describe, expect, it } from "vitest"

import { brand, levelColour, levelLabel } from "@/lib/theme"

describe("theme", () => {
  it("maps each hazard level to a brand colour", () => {
    expect(levelColour("low")).toBe(brand.green)
    expect(levelColour("medium")).toBe(brand.warning)
    expect(levelColour("high")).toBe(brand.risk)
  })

  it("has a plain-English label for every level", () => {
    expect(Object.keys(levelLabel).sort()).toEqual(["high", "low", "medium"])
  })
})
