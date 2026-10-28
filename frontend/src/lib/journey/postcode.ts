// UK postcode format check, mirroring backend/app/schemas/property.py and CONTRACT §1 rule 9.
// This only checks the *shape*; the API is what decides whether it's really covered (England and
// Wales only) and whether it resolves to a real address.
const POSTCODE = /^([A-Z]{1,2}[0-9][A-Z0-9]?)\s*([0-9][A-Z]{2})$/

export function normalisePostcode(raw: string): string | null {
  const m = POSTCODE.exec(raw.trim().toUpperCase())
  return m ? `${m[1]} ${m[2]}` : null
}

export function isPlausiblePostcode(raw: string): boolean {
  return normalisePostcode(raw) !== null
}

// Mostly-Welsh postcode areas. `PostcodeLookup` does not return `country` (docs/decisions/L.md,
// L7), so this is a best-effort guess for the `Address.country` label only — it never affects
// risk or scoring, which work from the postcode itself. `SY` genuinely straddles the border and
// will sometimes guess wrong.
const WELSH_AREAS = new Set(["CF", "LD", "LL", "NP", "SA", "SY"])

export function guessCountry(postcode: string): "england" | "wales" {
  const area = /^[A-Z]{1,2}/.exec(postcode.toUpperCase())?.[0] ?? ""
  return WELSH_AREAS.has(area) ? "wales" : "england"
}
