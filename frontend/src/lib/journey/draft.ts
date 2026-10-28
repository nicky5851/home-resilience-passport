// The in-progress "start a home" draft: address picked on /start, carried to /start/household.
// Lives in sessionStorage so it survives the forced login round trip (CONTRACT §4.4).
import type { AddressInput, HouseholdInput, PropertyFactsInput } from "@/lib/api/types"

const KEY = "hrp_start_draft"

export type StartDraft = {
  address: AddressInput
  property?: PropertyFactsInput | null
  household?: HouseholdInput
}

export function saveDraft(draft: StartDraft): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(draft))
  } catch {
    // Private browsing or storage disabled: the household form just starts blank.
  }
}

export function loadDraft(): StartDraft | null {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as StartDraft) : null
  } catch {
    return null
  }
}

export function clearDraft(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // Nothing to clear.
  }
}
