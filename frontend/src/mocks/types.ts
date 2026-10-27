import type {
  DemoHome,
  FundingBundle,
  HazardInputs,
  Passport,
  Plan,
  ResilienceScore,
  RiskProfile,
} from "@/lib/api/types"

/** One file in backend/tests/fixtures/demo_homes (spec §4.4). */
export type DemoFixture = DemoHome & {
  inputs: HazardInputs
  risk: RiskProfile
  score: ResilienceScore
  plan: Plan
  funding: FundingBundle
  passport: Passport
}
