# Scoring v1

L owns this file and `backend/app/scoring/`. The contract (field names, ranges, hazard order)
is fixed in `docs/CONTRACT.md`; everything below is the implementation of CODING_SPEC.md §6 and
may be tuned without a contract change (thresholds are first-version, reviewed with A at Merge 1).

Every threshold and weight is a named constant in `backend/app/scoring/config.py`. Nothing in this
document should disagree with that file; if it does, `config.py` is right and this file is stale.

## Risk engine (`app/scoring/risk.py`, step L4)

`assess_risk` is a pure function: given the same `HazardInputs` it always returns the same
`RiskProfile`. `today` is computed from the baseline inputs, `y2050` from the 2041–2050 inputs.
A missing (`null`) numeric input is scored `medium` and `why` says the data is unavailable
(CONTRACT.md §2 rule 52).

| Hazard | Low | Medium | High |
| --- | --- | --- | --- |
| River/sea flood | `rofrs_band` is `none` or `very_low` | `low` | `medium` or `high`; **+1 level** if `active_flood_warnings > 0` (capped at high) |
| Overheating | hot days < 5 | 5–15 | > 15; **+1 level** if `top_floor` is true or `epc_rating` is A/B (capped at high) |
| Storm | max sustained wind < 50 km/h | 50–65 | > 65 |
| Subsidence | `none_reported` | `unknown` | `clay_reported` or `cracks_reported` |
| Surface water | — fixed at `medium`/`medium` for M1 (no data source yet, CONTRACT.md §2) | | |

Notes:
- `rofrs_band` has no 2050 variant, so `today` and `y2050` are the same value for flood and
  subsidence (the EA band and the user's subsidence answer do not change with the climate
  projection).
- The flood warning bump and the heat bump each apply at most once; both cap at `high` rather
  than overflowing.
- `why` is a plain-English sentence (CONTRACT.md §1 rule 8, ≤140 characters), naming the data
  source where it exists ("The Environment Agency rates flood risk here as high.") or saying so
  plainly when a figure is missing ("Hot-day data for your postcode is unavailable, so this is
  scored as medium risk.").
- `RiskProfile.generated_at` is a fixed constant inside `risk.py`, not the system clock. A pure
  function cannot read "now" and stay deterministic (`test_functions_are_pure`,
  `test_assess_risk_contract`'s determinism check). The real timestamp is set by the assessment
  service (N9) when it stores the result — see `docs/decisions/L.md`.

## Resilience score (`app/scoring/score.py`, step L5)

`compute_score` is a pure function of `(RiskProfile, PropertyFacts, completed_measures)`. 100
points total: flood 30, heat 20, storm 10, subsidence 10 (resilience = 70%), carbon 30.

- Hazard points use the **2050** level (forward-looking): low = full marks, medium = half,
  high = 10% of the component's max (`LEVEL_FRACTION` in `config.py`). `surface_water` has no
  score component (spec §6 only lists 4 hazard components; it still shows on the risk page).
- Carbon points = `epc_score × 0.3`. If `epc_score` is `null` but `epc_rating` is known, use the
  band midpoint (A 96, B 86, C 75, D 61, E 47, F 30, G 10) × 0.3. If both are unknown, a flat 15
  points.
- Completed (or candidate) measures add their `resilience_points` to the component named by
  their `category`, each component capped at its max (a measure can't push a component past
  full marks). `hazards_reduced` does not move points directly — only `category` + `resilience_points`
  does.
- `value = round(sum(component.points))`, clamped to 0–100 (the clamp is a belt-and-braces
  safeguard; every component is already bounded `[0, max_points]` so the sum can't legally go
  outside 0–100, but the spec's check explicitly requires the score "never goes above 100 or
  below 0").
- Bands (`band_for`): A ≥ 85, B 70–84, C 55–69, D 40–54, E 25–39, F 10–24, G < 10.
- Each `ScoreComponent.reason` names the 2050 risk level and the points it's worth ("Your flood
  risk is high by 2050, worth 3 of 30 points."), or the EPC basis for carbon ("Based on your EPC
  score of 58."), plus a note when completed measures added points.

## Funding matcher (`app/scoring/funding.py`, step L6)

Not yet implemented (still the L3 stub). Will follow CODING_SPEC.md §7 Funding.
