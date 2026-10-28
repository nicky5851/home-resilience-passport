import { describe, expect, it } from "vitest"

import { guessCountry, isPlausiblePostcode, normalisePostcode } from "@/lib/journey/postcode"

describe("normalisePostcode", () => {
  it("uppercases and inserts one space", () => {
    expect(normalisePostcode("sw1a1aa")).toBe("SW1A 1AA")
    expect(normalisePostcode("  sw1a 1aa  ")).toBe("SW1A 1AA")
  })

  it("rejects anything that isn't postcode-shaped", () => {
    expect(normalisePostcode("not a postcode")).toBeNull()
    expect(normalisePostcode("")).toBeNull()
  })
})

describe("isPlausiblePostcode", () => {
  it("mirrors normalisePostcode", () => {
    expect(isPlausiblePostcode("EC1A 1BB")).toBe(true)
    expect(isPlausiblePostcode("12345")).toBe(false)
  })
})

describe("guessCountry", () => {
  it("guesses wales for mostly-Welsh areas", () => {
    expect(guessCountry("CF10 1AA")).toBe("wales")
    expect(guessCountry("LL30 1AA")).toBe("wales")
  })

  it("defaults to england otherwise", () => {
    expect(guessCountry("SW1A 1AA")).toBe("england")
    expect(guessCountry("M1 1AA")).toBe("england")
  })
})
