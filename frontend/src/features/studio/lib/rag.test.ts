import { describe, expect, it } from "vitest"

import { RAG_COLOR, ragBand, ragColor } from "./rag"

describe("ragBand", () => {
  it("maps every known low-severity word to low", () => {
    for (const w of ["none", "very low", "low", "excellent", "good"]) {
      expect(ragBand(w)).toBe("low")
    }
  })

  it("maps every known medium-severity word to medium", () => {
    for (const w of ["medium", "moderate", "average", "fair"]) {
      expect(ragBand(w)).toBe("medium")
    }
  })

  it("maps every known high-severity word to high", () => {
    for (const w of ["very high", "very_high", "high", "poor"]) {
      expect(ragBand(w)).toBe("high")
    }
  })

  it("is case- and whitespace-insensitive", () => {
    expect(ragBand(" HIGH ")).toBe("high")
  })

  it("returns undefined for an unrecognised word", () => {
    expect(ragBand("freeholder_needed")).toBeUndefined()
    expect(ragBand(null)).toBeUndefined()
    expect(ragBand(undefined)).toBeUndefined()
  })
})

describe("ragColor", () => {
  it("resolves a recognised band to its RAG token", () => {
    expect(ragColor("low")).toBe(RAG_COLOR.low)
    expect(ragColor("moderate")).toBe(RAG_COLOR.medium)
    expect(ragColor("very high")).toBe(RAG_COLOR.high)
  })

  it("falls back to a neutral colour for an unrecognised word", () => {
    expect(ragColor("freeholder_needed")).toBe("var(--s-stone-500)")
  })
})
