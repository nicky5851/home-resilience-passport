import { api, unwrap } from "@/lib/api/client"
import type { AddressInput, HouseholdInput, PropertyFactsInput } from "@/lib/api/types"

/** `POST /homes` then `POST /homes/{id}/assess` (CONTRACT §4.4, L8). */
export async function createAndAssessHome(
  address: AddressInput,
  household: HouseholdInput,
  property?: PropertyFactsInput | null,
): Promise<string> {
  const { home_id } = unwrap(
    await api.POST("/api/v1/homes", {
      body: { address, household, property_override: property ?? null },
    }),
  )
  unwrap(
    await api.POST("/api/v1/homes/{home_id}/assess", {
      params: { path: { home_id } },
    }),
  )
  return home_id
}
